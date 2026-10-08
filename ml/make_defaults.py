import json
import boto3
import pandas as pd

B = "cybersecurity-threat-detection-174797531196"
s3 = boto3.client("s3", region_name="eu-north-1")

spec = json.loads(s3.get_object(Bucket=B, Key="processed/columns.json")["Body"].read())
s3.download_file(B, "processed/train.csv", "/tmp/train.csv")
d = pd.read_csv("/tmp/train.csv", header=None)

# colonne 0 = cible, puis les features dans l'ordre de spec["columns"]
defaults = {c: float(d[i + 1].median()) for i, c in enumerate(spec["numeric"])}
s3.put_object(Bucket=B, Key="processed/defaults.json", Body=json.dumps(defaults).encode())
print(len(defaults), "valeurs par défaut écrites")