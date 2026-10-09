import sys

import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.parameters import ParameterFloat, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

REGION = "eu-north-1"
B = "cybersecurity-threat-detection-174797531196"
ROLE = "arn:aws:iam::174797531196:role/ctds-sagemaker-role"
GROUP = "ctds-xgboost-models"

# Usage : python build_pipeline.py [min_f1]   (défaut 0.89)
MIN_F1_VALUE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.89

session = PipelineSession(boto_session=boto3.Session(region_name=REGION), default_bucket=B)
xgb_image = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

# Paramètres externalisés
input_data = ParameterString("InputData", default_value=f"s3://{B}/raw/")
min_f1 = ParameterFloat("MinF1", default_value=0.89)
min_auc = ParameterFloat("MinAUC", default_value=0.95)

# --- Étape 1 : prétraitement ---
processor = SKLearnProcessor(
    framework_version="1.2-1", role=ROLE, instance_type="ml.m5.large",
    instance_count=1, sagemaker_session=session,
)
step_process = ProcessingStep(
    name="Preprocess",
    step_args=processor.run(
        code="sagemaker/pipeline/preprocess.py",
        inputs=[
            ProcessingInput(source=input_data, destination="/opt/ml/processing/input"),
            ProcessingInput(source="lambda/preprocessing.py", destination="/opt/ml/processing/lib"),
        ],
        outputs=[
            ProcessingOutput(
                output_name=n,
                source=f"/opt/ml/processing/output/{n}",
                destination=f"s3://{B}/pipeline/processed/{n}",
            )
            for n in ["train", "validation", "test", "spec"]
        ],
    ),
)
outputs = step_process.properties.ProcessingOutputConfig.Outputs

# --- Étape 2 : entraînement ---
est = Estimator(
    image_uri=xgb_image, role=ROLE, instance_count=1, instance_type="ml.m5.large",
    output_path=f"s3://{B}/pipeline/models/", max_run=1800,
    sagemaker_session=session, disable_profiler=True, debugger_hook_config=False,
)
est.set_hyperparameters(
    objective="binary:logistic", num_round=300, max_depth=5, eta=0.1,
    subsample=0.8, eval_metric="auc", early_stopping_rounds=20,
)
step_train = TrainingStep(
    name="Train",
    step_args=est.fit(inputs={
        "train": TrainingInput(outputs["train"].S3Output.S3Uri, content_type="text/csv"),
        "validation": TrainingInput(outputs["validation"].S3Output.S3Uri, content_type="text/csv"),
    }),
)

# --- Étape 3 : évaluation (image XGBoost 1.7-1 pour lire le modèle) ---
evaluator = ScriptProcessor(
    image_uri=xgb_image, command=["python3"], role=ROLE,
    instance_type="ml.m5.large", instance_count=1, sagemaker_session=session,
)
report = PropertyFile(name="EvaluationReport", output_name="evaluation", path="evaluation.json")
step_eval = ProcessingStep(
    name="Evaluate",
    step_args=evaluator.run(
        code="sagemaker/pipeline/evaluate_step.py",
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=outputs["test"].S3Output.S3Uri,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation",
                destination=f"s3://{B}/pipeline/evaluation",
            )
        ],
    ),
    property_files=[report],
)

# --- Étape 4 : enregistrement dans le Model Registry ---
step_register = RegisterModel(
    name="RegisterModel",
    estimator=est,
    model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    content_types=["text/csv"],
    response_types=["text/csv"],
    inference_instances=["ml.m5.large"],
    transform_instances=["ml.m5.large"],
    model_package_group_name=GROUP,
    approval_status="Approved",
)

# --- Étape 5 : condition de qualité (sinon, arrêt sans enregistrement) ---
step_cond = ConditionStep(
    name="CheckQuality",
    conditions=[
        ConditionGreaterThanOrEqualTo(
            left=JsonGet(step_name=step_eval.name, property_file=report, json_path="metrics.f1.value"),
            right=min_f1,
        ),
        ConditionGreaterThanOrEqualTo(
            left=JsonGet(step_name=step_eval.name, property_file=report, json_path="metrics.auc.value"),
            right=min_auc,
        ),
    ],
    if_steps=[step_register],
    else_steps=[],
)

pipeline = Pipeline(
    name="ctds-pipeline",
    parameters=[input_data, min_f1, min_auc],
    steps=[step_process, step_train, step_eval, step_cond],
    sagemaker_session=session,
)
pipeline.upsert(role_arn=ROLE)
execution = pipeline.start(parameters={"MinF1": MIN_F1_VALUE})
print("MinF1 =", MIN_F1_VALUE)
print("Exécution :", execution.arn)
print("Suivi : voir la commande de vérification, ne pas attendre dans ce terminal.")