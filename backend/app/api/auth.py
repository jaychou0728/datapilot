from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.service.auth_service import AuthService
from app.model.user import UserCreate, UserLogin
from app.utils.response import success, error
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])
svc = AuthService()


class UpdateRoleRequest(BaseModel):
    user_id: str
    role: str


@router.post("/register")
def register(req: UserCreate):
    try:
        user = svc.register(req.username, req.password)
        token = svc.create_token(user["id"])
        return success(data={"token": token, "user": user})
    except ValueError as e:
        return error(400, str(e))


@router.post("/login")
def login(req: UserLogin):
    try:
        user = svc.login(req.username, req.password)
        token = svc.create_token(user["id"])
        return success(data={"token": token, "user": user})
    except ValueError as e:
        return error(401, str(e))


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return success(data=user)


@router.get("/users")
def list_users(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        return error(403, "无权限")
    conn = get_db()
    rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return success(data=[dict(r) for r in rows])


@router.put("/role")
def update_role(req: UpdateRoleRequest, user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        return error(403, "无权限")
    if req.role not in ("admin", "user"):
        return error(400, "角色只能是 admin 或 user")
    conn = get_db()
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (req.role, req.user_id))
    conn.commit()
    conn.close()
    return success(message="角色已更新")
