import json, tarfile
import boto3, numpy as np, pandas as pd, xgboost as xgb
from sklearn.metrics import f1_score, precision_score, recall_score

B = "cybersecurity-threat-detection-174797531196"
s3 = boto3.client("s3", region_name="eu-north-1")

def load_csv(key):
    s3.download_file(B, key, "/tmp/x.csv")
    d = pd.read_csv("/tmp/x.csv", header=None)
    return d.iloc[:, 0].values, d.iloc[:, 1:].values

key = json.loads(s3.get_object(Bucket=B, Key="models/metrics.json")["Body"].read())["model_key"]
s3.download_file(B, key, "/tmp/model.tar.gz")
with tarfile.open("/tmp/model.tar.gz") as t:
    t.extractall("/tmp/model", filter="data")
booster = xgb.Booster()
booster.load_model("/tmp/model/xgboost-model")

yv, Xv = load_csv("processed/validation.csv")
yt, Xt = load_csv("processed/test.csv")
pv = booster.predict(xgb.DMatrix(Xv))
pt = booster.predict(xgb.DMatrix(Xt))

# 1. Seuil choisi sur la VALIDATION
grid = np.round(np.arange(0.1, 0.91, 0.05), 2)
best = max(grid, key=lambda th: f1_score(yv, pv >= th))
print("Seuil retenu (validation) :", best)
print("seuil | val F1 | test F1 | test precision | test recall")
for th in sorted({0.3, 0.5, 0.7, best}):
    print(th, round(f1_score(yv, pv >= th), 4), round(f1_score(yt, pt >= th), 4),
          round(precision_score(yt, pt >= th), 4), round(recall_score(yt, pt >= th), 4))

# 2. Attaques manquées par type (au seuil 0,5)
cat = pd.read_csv("/tmp/x.csv", header=None).shape[0]
s3.download_file(B, "raw/UNSW_NB15_testing-set.csv", "/tmp/raw_test.csv")
raw = pd.read_csv("/tmp/raw_test.csv", usecols=["attack_cat", "label"])
assert len(raw) == len(yt) and (raw["label"].values == yt).all(), "ordre différent"
raw["fn"] = (yt == 1) & (pt < 0.5)
att = raw[raw.label == 1].groupby("attack_cat")["fn"].agg(["sum", "count"])
att["taux_manque"] = (att["sum"] / att["count"]).round(3)
print(att.sort_values("sum", ascending=False))

# 3. Features les plus importantes
cols = json.loads(s3.get_object(Bucket=B, Key="processed/columns.json")["Body"].read())["columns"]
imp = booster.get_score(importance_type="gain")
top = sorted(imp.items(), key=lambda kv: -kv[1])[:8]
for k, v in top:
    print(cols[int(k[1:])], round(v, 1))