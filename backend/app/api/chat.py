from fastapi import APIRouter
from app.service.chat_service import ChatService
from app.config import DUCKDB_DIR
from app.utils.response import success, error
from app.model.chat import ChatRequest
import os

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest):
    db_path = os.path.join(DUCKDB_DIR, f"{req.dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = ChatService(duckdb_dir=DUCKDB_DIR)
    try:
        result = await svc.chat(req.dataset_id, req.message, req.history)
        return success(data=result.model_dump())
    except Exception as e:
        return error(500, str(e))
