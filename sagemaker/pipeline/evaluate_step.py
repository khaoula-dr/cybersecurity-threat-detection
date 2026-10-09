import json
import os
import tarfile

import numpy as np
import xgboost as xgb

MODEL_DIR = "/opt/ml/processing/model"
TEST_DIR = "/opt/ml/processing/test"
OUT_DIR = "/opt/ml/processing/evaluation"
THRESHOLD = 0.5


def auc_score(y, p):
    """AUC par les rangs (avec moyenne des rangs en cas d'égalité)."""
    order = np.argsort(p, kind="mergesort")
    _, inv, counts = np.unique(p[order], return_inverse=True, return_counts=True)
    avg_rank = np.cumsum(counts) - (counts - 1) / 2.0
    ranks = np.empty(len(p))
    ranks[order] = avg_rank[inv]
    n1 = int(y.sum())
    n0 = len(y) - n1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


with tarfile.open(f"{MODEL_DIR}/model.tar.gz") as t:
    t.extractall("/tmp/model")
booster = xgb.Booster()
booster.load_model("/tmp/model/xgboost-model")

data = np.loadtxt(f"{TEST_DIR}/test.csv", delimiter=",")
y, X = data[:, 0].astype(int), data[:, 1:]
proba = booster.predict(xgb.DMatrix(X))
pred = (proba >= THRESHOLD).astype(int)

tp = int(((pred == 1) & (y == 1)).sum())
fp = int(((pred == 1) & (y == 0)).sum())
fn = int(((pred == 0) & (y == 1)).sum())
tn = int(((pred == 0) & (y == 0)).sum())
precision = tp / (tp + fp)
recall = tp / (tp + fn)

metrics = {
    "auc": auc_score(y, proba),
    "f1": 2 * precision * recall / (precision + recall),
    "precision": precision,
    "recall": recall,
    "accuracy": (tp + tn) / len(y),
}
report = {
    "metrics": {k: {"value": v} for k, v in metrics.items()},
    "confusion": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    "threshold": THRESHOLD,
}
os.makedirs(OUT_DIR, exist_ok=True)
with open(f"{OUT_DIR}/evaluation.json", "w") as f:
    json.dump(report, f)
print(json.dumps(report))