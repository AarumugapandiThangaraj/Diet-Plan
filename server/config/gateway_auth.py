import json
import os
from functools import lru_cache

import boto3
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.conf import settings


class GatewayAuthError(Exception):
    pass


def get_bearer_token(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def verify_gateway_token(token):
    try:
        return jwt.decode(
            token,
            _gateway_public_key(),
            algorithms=[settings.GATEWAY_JWT_ALGORITHM],
            audience=settings.GATEWAY_JWT_AUDIENCE,
            issuer=settings.GATEWAY_JWT_ISSUER,
        )
    except Exception as exc:
        raise GatewayAuthError(str(exc)) from exc


def authenticate_gateway_request(request, required=True):
    existing_payload = getattr(request, "gateway_jwt_payload", None)
    if existing_payload:
        return existing_payload

    token = get_bearer_token(request)
    if not token:
        if required:
            raise GatewayAuthError("Authorization header missing or invalid")
        return None

    payload = verify_gateway_token(token)
    request.gateway_jwt_payload = payload
    request.gateway_user_id = payload.get("sub")
    return payload


def get_gateway_user_id(request, required=True):
    payload = authenticate_gateway_request(request, required=required)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id and required:
        raise GatewayAuthError("Gateway token does not include subject")
    return user_id


@lru_cache(maxsize=1)
def _gateway_public_key():
    configured_public_key = getattr(settings, "GATEWAY_JWT_PUBLIC_KEY", None)
    if configured_public_key:
        return configured_public_key

    secret_name = getattr(settings, "GATEWAY_JWT_SECRET_NAME", None)
    if not secret_name:
        raise GatewayAuthError("Gateway JWT public key is not configured")

    region_name = os.getenv("AWS_REGION", getattr(settings, "REGION_NAME", "ap-south-1"))
    client = boto3.client("secretsmanager", region_name=region_name)
    secret_res = client.get_secret_value(SecretId=secret_name)
    secret_string = secret_res.get("SecretString") or secret_res.get("SecretBinary", b"").decode("utf-8")
    secret = json.loads(secret_string)

    if secret.get("publicKey"):
        return secret["publicKey"]

    private_key_pem = secret.get("privateKey")
    if not private_key_pem:
        raise GatewayAuthError("Gateway JWT secret does not contain privateKey/publicKey")

    private_key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    public_key = private_key.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def get_optional_numeric_gateway_user_id(request):
    user_id = get_gateway_user_id(request, required=False)
    return user_id if user_id else None
