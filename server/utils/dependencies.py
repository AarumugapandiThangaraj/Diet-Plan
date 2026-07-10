from fastapi import Header, HTTPException, Request
from config.gateway_auth import get_gateway_user_id

async def get_user_id(gateway_user_id: str) -> str:
    # Stub: Replace with actual logic if needed
    return gateway_user_id

async def get_current_user_id(request: Request, x_user_id: str = Header(default="00000000-0000-0000-0000-000000000000")) -> str:
    """
    Dependency to extract the user ID.
    First tries to get it from the API Gateway JWT token.
    Falls back to 'x-user-id' header if token is missing or invalid.
    """
    try:
        gateway_user_id = get_gateway_user_id(request, required=False)
        if gateway_user_id:
            user_id = await get_user_id(gateway_user_id)
            if user_id:
                return user_id
    except Exception:
        pass  # Fallback to x_user_id if token validation fails

    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID is required")
    return x_user_id
