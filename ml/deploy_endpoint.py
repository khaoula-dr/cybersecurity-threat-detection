import boto3

REGION = "eu-north-1"
MODEL = "ctds-xgboost-v1"
CONFIG = "ctds-endpoint-config-v1"
ENDPOINT = "ctds-endpoint"

sm = boto3.client("sagemaker", region_name=REGION)

sm.create_endpoint_config(
    EndpointConfigName=CONFIG,
    ProductionVariants=[{
        "VariantName": "AllTraffic",
        "ModelName": MODEL,
        "InstanceType": "ml.m5.large",
        "InitialInstanceCount": 1,
    }],
)
sm.create_endpoint(EndpointName=ENDPOINT, EndpointConfigName=CONFIG)
print("Création lancée, attente (5 à 8 min)...")
sm.get_waiter("endpoint_in_service").wait(
    EndpointName=ENDPOINT, WaiterConfig={"Delay": 30, "MaxAttempts": 40}
)
print("Endpoint InService")