import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging_config import get_logger
from app.domains.detection.schemas import DetectionResult, FeatureContribution, FileActivityFeatures, ModelInfoResponse

logger = get_logger(__name__)

FEATURE_DESCRIPTIONS = {
    "file_modification_rate": "a high rate of file modifications",
    "file_rename_rate": "an unusually high file rename rate",
    "file_deletion_rate": "an elevated file deletion rate",
    "entropy_mean": "high content entropy consistent with encrypted data",
    "entropy_delta": "a sharp rise in file entropy versus baseline",
    "extension_change_ratio": "a large fraction of files changing extension",
    "unique_dirs_touched": "activity spread across many directories",
    "avg_size_change_ratio": "significant file size changes after modification",
    "process_cpu_percent": "elevated CPU usage by the responsible process",
    "io_write_rate_mb_s": "a high disk write throughput",
    "read_write_ratio": "a read/write pattern typical of bulk re-encoding",
}

# What a feature looks like when it pulls the decision TOWARD benign. A
# separate wording (rather than "the absence of <ransomware phrase>") so a
# benign verdict never reads as if e.g. "high content entropy" were the
# reason the activity looks safe.
BENIGN_DESCRIPTIONS = {
    "file_modification_rate": "a normal rate of file modifications",
    "file_rename_rate": "few or no file renames",
    "file_deletion_rate": "few or no deletions",
    "entropy_mean": "content entropy typical of ordinary documents",
    "entropy_delta": "no unusual rise in entropy versus baseline",
    "extension_change_ratio": "file extensions staying unchanged",
    "unique_dirs_touched": "activity confined to few directories",
    "avg_size_change_ratio": "file sizes staying stable",
    "process_cpu_percent": "modest CPU usage",
    "io_write_rate_mb_s": "modest disk write throughput",
    "read_write_ratio": "a normal read/write balance",
}

class ModelNotLoadedError(AppException):
    status_code = 503
    error_code = "MODEL_NOT_LOADED"

class DetectionService:
    _model = None
    _explainer = None
    _feature_names = None
    _metrics = None

    @classmethod
    def warm_up(cls) -> None:
        """
        Forces model/explainer/metrics loading immediately, rather than
        lazily on first use. Call this at application startup.

        WHY THIS MATTERS: joblib-deserializing the Random Forest model and
        SHAP explainer takes ~1.2s (measured). Without warming up, that
        entire delay lands on whichever request happens to be first —
        which, for the `monitoring` domain, means the FIRST observation
        window would call analyze() and unpredictably take over a second
        longer than every subsequent window. For a real-time detection
        system, that kind of latency variance on the very first detection
        is worth eliminating outright, not just tolerating.
        """
        cls._ensure_loaded()
        logger.info("Detection model warmed up and ready")

    @classmethod
    def _ensure_loaded(cls):
        if cls._model is not None:
            return
        try:
            cls._model = joblib.load(settings.ML_MODEL_PATH)
            cls._explainer = joblib.load(settings.ML_EXPLAINER_PATH)
            cls._feature_names = joblib.load(settings.ML_FEATURE_NAMES_PATH)
            metrics_path = Path(settings.ML_MODEL_PATH).parent / "metrics.json"
            with open(metrics_path) as f:
                cls._metrics = json.load(f)
        except FileNotFoundError as exc:
            raise ModelNotLoadedError("Detection model artifacts are not available.", details={"missing_file": str(exc)}) from exc

    @classmethod
    def _extract_shap_row(cls, shap_values, row_idx):
        if isinstance(shap_values, list):
            return shap_values[1][row_idx]
        if shap_values.ndim == 3:
            return shap_values[row_idx, :, 1]
        return shap_values[row_idx]

    @classmethod
    def analyze(cls, features: FileActivityFeatures) -> DetectionResult:
        cls._ensure_loaded()
        row = pd.DataFrame([[getattr(features, name) for name in cls._feature_names]], columns=cls._feature_names)
        proba = cls._model.predict_proba(row)[0]
        confidence_ransomware = float(proba[1])
        prediction = "ransomware_like" if confidence_ransomware >= 0.5 else "benign"
        confidence = confidence_ransomware if prediction == "ransomware_like" else float(proba[0])
        shap_raw = cls._explainer.shap_values(row)
        shap_row = cls._extract_shap_row(shap_raw, 0)
        contributions = []
        for name, value, shap_val in zip(cls._feature_names, row.iloc[0].values, shap_row):
            contributions.append(FeatureContribution(feature=name, value=round(float(value), 4), shap_value=round(float(shap_val), 4), direction="increases_risk" if shap_val > 0 else "decreases_risk"))
        if prediction == "ransomware_like":
            top = sorted(contributions, key=lambda c: c.shap_value, reverse=True)[:4]
            top = [c for c in top if c.shap_value > 0] or top[:1]
        else:
            top = sorted(contributions, key=lambda c: c.shap_value)[:4]
            top = [c for c in top if c.shap_value < 0] or top[:1]
        explanation_summary = cls._build_explanation(prediction, confidence, top)
        return DetectionResult(prediction=prediction, confidence=round(confidence, 4), threat_score=round(confidence_ransomware * 100, 2), top_contributing_features=top, explanation_summary=explanation_summary)

    @staticmethod
    def _build_explanation(prediction, confidence, top):
        descriptions = FEATURE_DESCRIPTIONS if prediction == "ransomware_like" else BENIGN_DESCRIPTIONS
        reasons = [descriptions.get(c.feature, c.feature) for c in top[:3]]
        reason_text = (", ".join(reasons[:-1]) + f", and {reasons[-1]}") if len(reasons) > 1 else (reasons[0] if reasons else "no strongly distinguishing indicators")
        if prediction == "ransomware_like":
            return f"Flagged as ransomware-like with {confidence:.0%} confidence, primarily due to {reason_text}."
        return f"Classified as benign with {confidence:.0%} confidence, mainly because of {reason_text}."

    @classmethod
    def get_model_info(cls) -> ModelInfoResponse:
        cls._ensure_loaded()
        return ModelInfoResponse(model_type=cls._metrics["model_type"], feature_names=cls._feature_names, training_accuracy=cls._metrics["accuracy"], training_f1_score=cls._metrics["f1_score"], training_roc_auc=cls._metrics["roc_auc"])

    @classmethod
    def simulate_features(cls, scenario: str, rng: np.random.Generator) -> FileActivityFeatures:
        """
        Generates one synthetic feature sample matching the SAME distributions
        used to train the model (see /ml/data/generate_dataset.py). This lets
        the detection engine be demoed end-to-end without needing the
        real-time Watchdog/Psutil monitor to be actively watching a directory.
        """
        if scenario == "benign":
            sample = {
                "file_modification_rate": float(rng.gamma(1.5, 1.2)),
                "file_rename_rate": float(rng.gamma(0.8, 0.3)),
                "file_deletion_rate": float(rng.gamma(0.6, 0.25)),
                "entropy_mean": float(np.clip(rng.normal(4.2, 1.2), 0, 8)),
                "entropy_delta": float(rng.normal(0.15, 0.6)),
                "extension_change_ratio": float(rng.beta(1.2, 12)),
                "unique_dirs_touched": float(rng.poisson(1.8)),
                "avg_size_change_ratio": float(max(rng.normal(1.02, 0.10), 0.5)),
                "process_cpu_percent": float(np.clip(rng.gamma(2.0, 6.0), 0, 100)),
                "io_write_rate_mb_s": float(rng.gamma(1.2, 0.8)),
                "read_write_ratio": float(max(rng.normal(2.4, 1.2), 0.1)),
            }
        elif scenario == "ransomware_stealthy":
            sample = {
                "file_modification_rate": float(rng.gamma(1.8, 1.8)),
                "file_rename_rate": float(rng.gamma(1.2, 0.9)),
                "file_deletion_rate": float(rng.gamma(0.7, 0.5)),
                "entropy_mean": float(np.clip(rng.normal(6.6, 0.9), 0, 8)),
                "entropy_delta": float(rng.normal(1.6, 0.8)),
                "extension_change_ratio": float(rng.beta(3.5, 4)),
                "unique_dirs_touched": float(rng.poisson(2.8)),
                "avg_size_change_ratio": float(max(rng.normal(1.10, 0.15), 0.5)),
                "process_cpu_percent": float(np.clip(rng.gamma(2.5, 6.5), 0, 100)),
                "io_write_rate_mb_s": float(rng.gamma(1.8, 1.3)),
                "read_write_ratio": float(max(rng.normal(1.6, 0.7), 0.05)),
            }
        else:  # ransomware_typical
            sample = {
                "file_modification_rate": float(rng.gamma(6.0, 7.0)),
                "file_rename_rate": float(rng.gamma(5.0, 5.5)),
                "file_deletion_rate": float(rng.gamma(2.5, 2.0)),
                "entropy_mean": float(np.clip(rng.normal(7.5, 0.5), 0, 8)),
                "entropy_delta": float(rng.normal(2.8, 1.0)),
                "extension_change_ratio": float(rng.beta(8, 2.5)),
                "unique_dirs_touched": float(rng.poisson(8.5)),
                "avg_size_change_ratio": float(max(rng.normal(1.15, 0.22), 0.5)),
                "process_cpu_percent": float(np.clip(rng.gamma(6.0, 9.0), 0, 100)),
                "io_write_rate_mb_s": float(rng.gamma(5.0, 4.0)),
                "read_write_ratio": float(max(rng.normal(1.1, 0.5), 0.05)),
            }
        return FileActivityFeatures(**sample)