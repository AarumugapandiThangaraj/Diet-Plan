from utils.database import get_user_id
from config.gateway_auth import get_gateway_user_id
from fastapi import Header, HTTPException, Request



async def get_current_user_id(request: Request) -> str:
    """
    Dependency to extract the user ID.
    First tries to get it from the API Gateway JWT token.
    Falls back to 'x-user-id' header if token is missing or invalid.
    """
    try:
        print("header", request.headers)
        gateway_user_id = get_gateway_user_id(request, required=False)


        print("gateway_user_id", gateway_user_id)
        if gateway_user_id:
            print("Going to get user _id")
            user_id = await get_user_id(gateway_user_id)
            print("userid from jwt", user_id)
            if user_id:
                return user_id
    except Exception as e:
        print("Exception in get_current_user_id", e)  

    # Fallback to x-user-id header
    user_id = request.headers.get("x-user-id")
    if user_id:
        return user_id

    raise HTTPException(status_code=401, detail="User identification missing")
