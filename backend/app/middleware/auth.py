from fastapi import Request
from app.service.auth_service import AuthService
from app.config import DEFAULT_USER_ID

_auth_service = AuthService()

async def get_current_user(request: Request) -> dict:
    """Returns {id, username, role}. Falls back to default user if no token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = _auth_service.verify_token(token)
        if user_id:
            user = _auth_service.get_user(user_id)
            if user:
                return {"id": user["id"], "username": user["username"], "role": user.get("role", "user")}
    return {"id": DEFAULT_USER_ID, "username": "default", "role": "user"}

async def get_current_user_id(request: Request) -> str:
    user = await get_current_user(request)
    return user["id"]
