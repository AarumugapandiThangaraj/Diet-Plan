from fastapi import Header, HTTPException

def get_current_user_id(x_user_id: str = Header(default="00000000-0000-0000-0000-000000000000")) -> str:
    """
    Dependency to extract the user ID from the 'x-user-id' header.
    Defaults to the mock UUID if not provided for backwards compatibility.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="User ID is required in headers")
    return x_user_id
