"""
Trains the Random Forest ransomware-behavior classifier, evaluates it
rigorously, and fits a SHAP TreeExplainer for explainability.
"""

import json

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score,
)
from sklearn.model_selection import train_test_split, cross_val_score

RANDOM_SEED = 42

FEATURE_NAMES = [
    "file_modification_rate", "file_rename_rate", "file_deletion_rate",
    "entropy_mean", "entropy_delta", "extension_change_ratio",
    "unique_dirs_touched", "avg_size_change_ratio", "process_cpu_percent",
    "io_write_rate_mb_s", "read_write_ratio",
]


def main():
    df = pd.read_csv("data/behavioral_dataset.csv")
    X = df[FEATURE_NAMES]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=5,
        random_state=RANDOM_SEED, n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred)
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="f1")

    report_text = "\n".join([
        "EarlyShield — Random Forest Detection Model",
        "=" * 60,
        f"Training samples: {len(X_train)} | Test samples: {len(X_test)}",
        "",
        f"Accuracy:  {acc:.4f}",
        f"Precision: {prec:.4f}",
        f"Recall:    {rec:.4f}",
        f"F1 Score:  {f1:.4f}",
        f"ROC-AUC:   {auc:.4f}",
        f"5-fold CV F1: mean={cv_scores.mean():.4f}, std={cv_scores.std():.4f}",
        "",
        "Confusion Matrix:",
        "                 Predicted Benign   Predicted Ransomware",
        f"Actual Benign         {cm[0][0]:>6}              {cm[0][1]:>6}",
        f"Actual Ransomware     {cm[1][0]:>6}              {cm[1][1]:>6}",
        "",
        classification_report(y_test, y_pred, target_names=["Benign", "Ransomware-like"]),
    ])
    print(report_text)
    with open("reports/evaluation_report.txt", "w") as f:
        f.write(report_text)

    importances = pd.Series(model.feature_importances_, index=FEATURE_NAMES).sort_values()
    plt.figure(figsize=(8, 6))
    importances.plot(kind="barh", color="#1F497D")
    plt.title("Random Forest Feature Importance")
    plt.xlabel("Importance")
    plt.tight_layout()
    plt.savefig("reports/feature_importance.png", dpi=150)
    plt.close()

    explainer = shap.TreeExplainer(model)
    sample = X_test.sample(n=min(500, len(X_test)), random_state=RANDOM_SEED)
    shap_values = explainer.shap_values(sample)
    if isinstance(shap_values, list):
        sv_for_class1 = shap_values[1]
    elif shap_values.ndim == 3:
        sv_for_class1 = shap_values[:, :, 1]
    else:
        sv_for_class1 = shap_values

    plt.figure()
    shap.summary_plot(sv_for_class1, sample, feature_names=FEATURE_NAMES, show=False)
    plt.tight_layout()
    plt.savefig("reports/shap_summary.png", dpi=150)
    plt.close()

    joblib.dump(model, "models/ransomware_rf_model.joblib")
    joblib.dump(explainer, "models/shap_explainer.joblib")
    joblib.dump(FEATURE_NAMES, "models/feature_names.joblib")

    metrics = {
        "model_type": "RandomForestClassifier",
        "n_estimators": model.n_estimators,
        "max_depth": model.max_depth,
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1_score": round(float(f1), 4),
        "roc_auc": round(float(auc), 4),
        "cv_f1_mean": round(float(cv_scores.mean()), 4),
        "cv_f1_std": round(float(cv_scores.std()), 4),
    }
    with open("models/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print("\nSaved all model artifacts and reports.")


if __name__ == "__main__":
    main()
