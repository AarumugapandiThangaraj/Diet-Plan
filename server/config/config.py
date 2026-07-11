from urllib.parse import quote_plus
import ast
from botocore.exceptions import ClientError
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

env = os.getenv("ENV", "dev")


if env == "newuat":
    ssm_path = "/twellr_uae_uat"
elif env == "uat":
    ssm_path = "/twellr_uae_uat"
elif env == "prod":
    ssm_path = "/twellr_uae_prod"
else:
    ssm_path = "/twellr_uae"

ssm_client = boto3.client("ssm", region_name="ap-south-1")

# --------------------------------------
# Get SSM Parameter (Safe)
# --------------------------------------
def get_parameter(name, default=None):
    try:
        response = ssm_client.get_parameter(
            Name=name,
            WithDecryption=True
        )
        value = response["Parameter"]["Value"]

        try:
            return ast.literal_eval(value)
        except Exception:
            return value

    except ClientError:
        return default


BUCKET_NAME = get_parameter(f"{ssm_path}/BUCKET_NAME")
EXP_IN = 300  # 5 minutes
CLOUDFRONT_DOMAIN = get_parameter(f'{ssm_path}/CLOUDFRONT_URL') # "d2h8l7n9g5j1o.cloudfront.net"
DATABASE_SCHEMA = get_parameter(f'{ssm_path}/DATABASE_SCHEMA')
S3_CLIENT = boto3.client("s3", region_name="ap-south-1")
AWS_REGION = get_parameter(f'{ssm_path}/REGION_NAME') # "ap-south-1"
FROM_EMAIL = get_parameter(f'{ssm_path}/NOREPLY_EMAIL') # "saravanakumar.ramasundaram@iagami.com"
LOGO_URL = "https://d1eyy17dbqmkdr.cloudfront.net/twellr_logo.png" # get_parameter(f'{ssm_path}/TWELLR_PDF_LOGO_URL')

GATEWAY_JWT_ISSUER = get_parameter(f'{ssm_path}/GATEWAY_JWT_ISS')
GATEWAY_JWT_AUDIENCE = "fastapi" # get_parameter(f'{ssm_path}/GATEWAY_JWT_AUD_ANALYSIS')
GATEWAY_JWT_ALGORITHM = get_parameter(f'{ssm_path}/GATEWAY_JWT_ALG')
GATEWAY_JWT_SECRET_NAME = get_parameter(f'{ssm_path}/GATEWAY_JWT_SECRET_NAME')
GATEWAY_JWT_PUBLIC_KEY = get_parameter(f'{ssm_path}/PRIVATE_KEY')


def build_database_url():
    user = str(get_parameter(f"{ssm_path}/DATABASE_USER")).strip()
    password = quote_plus(str(get_parameter(f"{ssm_path}/DATABASE_PASSWORD")).strip())
    host = str(get_parameter(f"{ssm_path}/DATABASE_HOST")).strip()
    port = str(get_parameter(f"{ssm_path}/DATABASE_PORT")).strip()
    name = str(get_parameter(f"{ssm_path}/DATABASE_NAME")).strip()
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = build_database_url()