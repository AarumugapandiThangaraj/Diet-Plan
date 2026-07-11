import boto3
import ast

ssm_client = boto3.client("ssm", region_name="ap-south-1")

def get_param(name):
    try:
        res = ssm_client.get_parameter(Name=name, WithDecryption=True)
        return res["Parameter"]["Value"]
    except Exception as e:
        return f"Error: {e}"

for path in ["/twellr_uae", "/twellr_uae_uat", "/twellr_uae_prod"]:
    print(f"\n--- {path} ---")
    print("Host:", get_param(f"{path}/DATABASE_HOST"))
    print("Name:", get_param(f"{path}/DATABASE_NAME"))
    print("Schema:", get_param(f"{path}/DATABASE_SCHEMA"))
