import io
import json

import pandas as pd

TARGET = "label"
DROP_COLS = ["id", "attack_cat", "stcpb", "dtcpb", "ct_ftp_cmd"]
CAT_COLS = ["proto", "service", "state"]
TOP_PROTO = 5


def stratified_split(df, frac=0.2, seed=42):
    """Sépare df en (train, validation), stratifié sur la cible."""
    val = df.groupby(TARGET, group_keys=False).sample(frac=frac, random_state=seed)
    return df.drop(val.index), val


def fit_spec(train_df):
    """Apprend les catégories sur le train uniquement (pas de fuite)."""
    protos = train_df["proto"].value_counts().head(TOP_PROTO).index.tolist()
    numeric = [c for c in train_df.columns if c not in DROP_COLS + CAT_COLS + [TARGET]]
    spec = {
        "numeric": numeric,
        "protos": protos,
        "service": sorted(train_df["service"].unique().tolist()),
        "state": sorted(train_df["state"].unique().tolist()),
    }
    spec["columns"] = (
        numeric
        + [f"proto_{p}" for p in protos + ["other"]]
        + [f"service_{s}" for s in spec["service"]]
        + [f"state_{s}" for s in spec["state"]]
    )
    return spec


def transform(df, spec):
    """Applique la spec : colonnes dans un ordre fixe, catégories inconnues = 0."""
    parts = {c: df[c] for c in spec["numeric"]}
    proto = df["proto"].where(df["proto"].isin(spec["protos"]), "other")
    for v in spec["protos"] + ["other"]:
        parts[f"proto_{v}"] = (proto == v).astype(int)
    for col in ["service", "state"]:
        for v in spec[col]:
            parts[f"{col}_{v}"] = (df[col] == v).astype(int)
    return pd.DataFrame(parts)[spec["columns"]]


def to_csv_bytes(df, features):
    """Format SageMaker XGBoost : cible en 1re colonne, sans en-tête."""
    out = pd.concat([df[TARGET].reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    return out.to_csv(header=False, index=False).encode()


def handler(event, context):
    import boto3

    s3 = boto3.client("s3")
    bucket = event["Records"][0]["s3"]["bucket"]["name"]

    def read(key):
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        return pd.read_csv(io.BytesIO(body))

    full = read("raw/UNSW_NB15_training-set.csv")
    test = read("raw/UNSW_NB15_testing-set.csv")

    train, val = stratified_split(full)
    spec = fit_spec(train)

    for name, df in [("train", train), ("validation", val), ("test", test)]:
        body = to_csv_bytes(df, transform(df, spec))
        s3.put_object(Bucket=bucket, Key=f"processed/{name}.csv", Body=body)
        print(f"{name}: {len(df)} lignes")

    s3.put_object(Bucket=bucket, Key="processed/columns.json", Body=json.dumps(spec).encode())
    return {"status": "ok", "n_features": len(spec["columns"])}