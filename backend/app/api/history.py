from fastapi import APIRouter, Depends, Query
from app.middleware.auth import get_current_user
from app.service.history_service import HistoryService
from app.utils.response import success

router = APIRouter(prefix="/api/history", tags=["history"])
svc = HistoryService()

@router.get("")
async def list_history(user: dict = Depends(get_current_user), type: str | None = Query(None)):
    if user["role"] == "admin":
        return success(data=svc.list_all(type))
    return success(data=svc.list_by_user(user["id"], type))
