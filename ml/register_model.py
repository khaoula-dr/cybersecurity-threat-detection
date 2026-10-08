import json

import boto3
import sagemaker

REGION = "eu-north-1"
B = "cybersecurity-threat-detection-174797531196"
ROLE = "arn:aws:iam::174797531196:role/ctds-sagemaker-role"
GROUP = "ctds-xgboost-models"

sm = boto3.client("sagemaker", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

# Métriques et modèle produits par evaluate.py
m = json.loads(s3.get_object(Bucket=B, Key="models/metrics.json")["Body"].read())
model_data = f"s3://{B}/{m['model_key']}"
image = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

# 1. Groupe de modèles (créé une seule fois)
try:
    sm.create_model_package_group(
        ModelPackageGroupName=GROUP,
        ModelPackageGroupDescription="Détection de menaces réseau (UNSW-NB15, XGBoost)",
    )
    print("Groupe créé")
except sm.exceptions.ClientError as e:
    print("Groupe existant ou erreur :", e.response["Error"]["Message"])

# 2. Nouvelle version, avec ses métriques
pkg = sm.create_model_package(
    ModelPackageGroupName=GROUP,
    ModelPackageDescription="XGBoost 1.7-1, seuil 0.5, évalué sur le test officiel",
    InferenceSpecification={
        "Containers": [{"Image": image, "ModelDataUrl": model_data}],
        "SupportedContentTypes": ["text/csv"],
        "SupportedResponseMIMETypes": ["text/csv"],
    },
    ModelApprovalStatus="Approved",
    CustomerMetadataProperties={
        "auc": f"{m['auc']:.4f}",
        "f1": f"{m['f1']:.4f}",
        "recall": f"{m['recall']:.4f}",
        "precision": f"{m['precision']:.4f}",
        "threshold": "0.5",
        "dataset": "UNSW-NB15",
    },
)
arn = pkg["ModelPackageArn"]
print("Version enregistrée :", arn)

# 3. Objet Model SageMaker, créé depuis la version enregistrée
version = arn.split("/")[-1]
name = f"ctds-xgboost-v{version}"
sm.create_model(
    ModelName=name,
    ExecutionRoleArn=ROLE,
    PrimaryContainer={"ModelPackageName": arn},
)
print("Modèle SageMaker créé :", name)