import json
import os

THRESHOLD = 0.5
_cache = {}


def build_row(features, spec, defaults):
    """Construit la ligne CSV dans l'ordre exact de spec['columns']."""
    row = {c: float(features.get(c, defaults[c])) for c in spec["numeric"]}
    proto = features.get("proto", "other")
    if proto not in spec["protos"]:
        proto = "other"
    for v in spec["protos"] + ["other"]:
        row[f"proto_{v}"] = 1.0 if proto == v else 0.0
    for col in ["service", "state"]:
        val = features.get(col)
        for v in spec[col]:
            row[f"{col}_{v}"] = 1.0 if val == v else 0.0
    return [row[c] for c in spec["columns"]]


def classify(proba):
    return {
        "prediction": "Suspicious" if proba >= THRESHOLD else "Normal",
        "probability": round(proba, 4),
    }


def _load(key):
    if key not in _cache:
        import boto3
        s3 = boto3.client("s3")
        body = s3.get_object(Bucket=os.environ["BUCKET"], Key=key)["Body"].read()
        _cache[key] = json.loads(body)
    return _cache[key]


def handler(event, context):
    import boto3

    body = event.get("body", event)
    features = json.loads(body) if isinstance(body, str) else body

    spec = _load("processed/columns.json")
    defaults = _load("processed/defaults.json")
    row = build_row(features, spec, defaults)

    rt = boto3.client("sagemaker-runtime")
    r = rt.invoke_endpoint(
        EndpointName=os.environ.get("ENDPOINT", "ctds-endpoint"),
        ContentType="text/csv",
        Body=",".join(str(v) for v in row),
    )
    proba = float(r["Body"].read().decode().strip())
    result = classify(proba)
    print(json.dumps({"input_keys": sorted(features), **result}))
    return result