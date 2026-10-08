import json
import tarfile
import boto3
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix)

B = "cybersecurity-threat-detection-174797531196"
s3 = boto3.client("s3", region_name="eu-north-1")

# 1. Retrouver le dernier model.tar.gz
objs = s3.list_objects_v2(Bucket=B, Prefix="models/")["Contents"]
key = max((o for o in objs if o["Key"].endswith("model.tar.gz")),
          key=lambda o: o["LastModified"])["Key"]
print("Modèle :", key)
s3.download_file(B, key, "/tmp/model.tar.gz")
with tarfile.open("/tmp/model.tar.gz") as t:
    t.extractall("/tmp/model")

booster = xgb.Booster()
booster.load_model("/tmp/model/xgboost-model")

# 2. Charger le test (cible en 1re colonne, sans en-tête)
s3.download_file(B, "processed/test.csv", "/tmp/test.csv")
test = pd.read_csv("/tmp/test.csv", header=None)
y, X = test.iloc[:, 0].values, test.iloc[:, 1:].values

# 3. Prédire et calculer les métriques
proba = booster.predict(xgb.DMatrix(X))
pred = (proba >= 0.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y, pred).ravel()

metrics = {
    "accuracy": accuracy_score(y, pred),
    "precision": precision_score(y, pred),
    "recall": recall_score(y, pred),
    "f1": f1_score(y, pred),
    "auc": roc_auc_score(y, proba),
    "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    "model_key": key,
}
print(json.dumps(metrics, indent=2))

s3.put_object(Bucket=B, Key="models/metrics.json", Body=json.dumps(metrics).encode())