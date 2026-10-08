import boto3

sm = boto3.client("sagemaker", region_name="eu-north-1")
for fn, kw in [(sm.delete_endpoint, {"EndpointName": "ctds-endpoint"}),
               (sm.delete_endpoint_config, {"EndpointConfigName": "ctds-endpoint-config-v1"})]:
    try:
        fn(**kw)
        print("Supprimé :", list(kw.values())[0])
    except Exception as e:
        print("Ignoré :", e)