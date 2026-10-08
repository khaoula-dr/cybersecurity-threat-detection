import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput

REGION = "eu-north-1"
B = "cybersecurity-threat-detection-174797531196"
ROLE = "arn:aws:iam::174797531196:role/ctds-sagemaker-role"

session = sagemaker.Session(boto3.Session(region_name=REGION))
image = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

est = Estimator(
    image_uri=image,
    role=ROLE,
    instance_count=1,
    instance_type="ml.m5.large",
    output_path=f"s3://{B}/models/",
    max_run=1800,  # coupe le job après 30 min, protection coût
    sagemaker_session=session,
)
est.set_hyperparameters(
    objective="binary:logistic",
    num_round=300,
    max_depth=5,
    eta=0.1,
    subsample=0.8,
    eval_metric="auc",
    early_stopping_rounds=20,
)
est.fit({
    "train": TrainingInput(f"s3://{B}/processed/train.csv", content_type="text/csv"),
    "validation": TrainingInput(f"s3://{B}/processed/validation.csv", content_type="text/csv"),
})
print("Artefact :", est.model_data)