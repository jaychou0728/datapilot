from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.service.cleaning_service import CleaningService
from app.service.history_service import HistoryService
from app.service.lineage_service import LineageService
from app.config import DUCKDB_DIR
from app.middleware.auth import get_current_user_id
from app.utils.response import success, error
from app.model.cleaning import CleanRequest
import os

router = APIRouter(prefix="/api/cleaning", tags=["cleaning"])
hist_svc = HistoryService()
lineage_svc = LineageService()


class AiExecuteRequest(BaseModel):
    operations: list[dict]


@router.post("/{dataset_id}/analyze")
async def ai_analyze(dataset_id: str):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = CleaningService(db_path=db_path, table_name="data")
    try:
        result = await svc.ai_analyze()
        return success(data=result)
    except Exception as e:
        return error(500, str(e))


@router.post("/{dataset_id}/execute")
def execute_cleaning(dataset_id: str, req: CleanRequest, user_id: str = Depends(get_current_user_id)):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = CleaningService(db_path=db_path, table_name="data")
    try:
        result = svc.execute(req.actions, req.fill_strategy)
        hist_svc.log(user_id, "clean", f"清洗数据：{'、'.join(result.changes)}", dataset_id)
        for change in result.changes:
            lineage_svc.log(user_id, dataset_id, None, "clean", "table:data", change, {}, {})
        return success(data=result.model_dump())
    except Exception as e:
        return error(500, str(e))


@router.post("/{dataset_id}/ai-execute")
async def ai_execute(dataset_id: str, req: AiExecuteRequest, user_id: str = Depends(get_current_user_id)):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = CleaningService(db_path=db_path, table_name="data")
    try:
        result = await svc.ai_execute(req.operations)
        hist_svc.log(user_id, "clean", f"AI清洗：{'、'.join(result.changes)}", dataset_id)
        for change in result.changes:
            lineage_svc.log(user_id, dataset_id, None, "clean", "table:data", change, {}, {})
        return success(data=result.model_dump())
    except Exception as e:
        return error(500, str(e))


@router.post("/{dataset_id}/undo")
def undo(dataset_id: str):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    svc = CleaningService(db_path=db_path, table_name="data")
    ok = svc.undo()
    if ok:
        return success(message="已撤销")
    return error(400, "没有可撤销的操作")
