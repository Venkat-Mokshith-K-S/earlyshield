# EarlyShield — ML Detection Engine

Trains the Random Forest classifier + SHAP explainer powering the
`detection` domain (`POST /api/v1/detection/analyze`).

## Why synthetic training data

Training on real ransomware requires executing live malware, which is
unsafe, potentially illegal outside a properly isolated sandbox, and out
of scope for an academic mini-project. Instead, this pipeline simulates
the behavioral signatures documented in the ransomware-detection
literature (Hirano & Kobayashi 2019; Urooj et al. 2022; Vehabovic et al.
2023 — see the project References). Classes deliberately overlap
(legitimate bursty software vs. stealthy low-and-slow ransomware) so the
model has genuine decision boundaries to learn, not a trivial threshold.

## Current model performance (models/metrics.json)

| Metric | Value |
|---|---|
| Accuracy | 96.79% |
| Precision | 96.75% |
| Recall | 96.83% |
| F1 Score | 0.968 |
| ROC-AUC | 0.980 |
| 5-fold CV F1 | 0.971 ± 0.003 |

## Retraining

```bash
cd ml
pip install -r requirements.txt
python data/generate_dataset.py
python train/train_model.py
```

Always train in a fresh virtualenv from `requirements.txt`. The `.joblib`
files are pickles, so the scikit-learn/shap/numpy versions used for training
must match the versions pinned in `backend/requirements.txt`; otherwise
scikit-learn raises `InconsistentVersionWarning` and predictions are not
guaranteed to be correct. (An earlier build of these artifacts came from
scikit-learn 1.8.0 by accident. They were retrained with the pinned 1.5.2
on 2026-10-22 and every metric came out identical.)

Then copy the new artifacts into the backend:
```bash
cp models/*.joblib models/metrics.json ../backend/app/ml_models/
```
