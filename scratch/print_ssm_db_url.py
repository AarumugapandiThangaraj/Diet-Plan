import asyncio
import boto3
import ast
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

ssm_client = boto3.client("ssm", region_name="ap-south-1")
ssm_path = "/twellr_uae"

def get_parameter(name):
    try:
        response = ssm_client.get_parameter(Name=name, WithDecryption=True)
        value = response["Parameter"]["Value"]
        try:
            return ast.literal_eval(value)
        except Exception:
            return value
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return None

user = get_parameter(f"{ssm_path}/DATABASE_USER")
host = get_parameter(f"{ssm_path}/DATABASE_HOST")
port = get_parameter(f"{ssm_path}/DATABASE_PORT")
name = get_parameter(f"{ssm_path}/DATABASE_NAME")
schema = get_parameter(f"{ssm_path}/DATABASE_SCHEMA")

print(f"User: {user}")
print(f"Host: {host}")
print(f"Port: {port}")
print(f"Name: {name}")
print(f"Schema: {schema}")
