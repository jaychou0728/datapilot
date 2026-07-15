from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.service.cleaning_service import CleaningService
from app.service.history_service import HistoryService
from app.service.lineage_service import LineageService
from app.service.version_service import VersionService
from app.config import DUCKDB_DIR
from app.middleware.auth import get_current_user_id
from app.utils.response import success, error
from app.model.cleaning import CleanRequest
import os

router = APIRouter(prefix="/api/cleaning", tags=["cleaning"])
hist_svc = HistoryService()
lineage_svc = LineageService()
version_svc = VersionService()


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
        version_svc.create(dataset_id, f"清洗前快照", db_path=db_path, duckdb_dir=DUCKDB_DIR)
        result = svc.execute(req.actions, req.fill_strategy)
        hist_svc.log(user_id, "clean", f"清洗数据：{'、'.join(result.changes)}", dataset_id)
        lineage_svc.log(user_id, dataset_id, None, "clean", "table:data",
                        f"规则清洗：{'、'.join(result.changes)}",
                        {"row_count": result.rows_before, "columns_count": 0},
                        {"row_count": result.rows_after, "columns_count": 0})
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
        version_svc.create(dataset_id, f"AI清洗前快照", db_path=db_path, duckdb_dir=DUCKDB_DIR)
        result = await svc.ai_execute(req.operations)
        hist_svc.log(user_id, "clean", f"AI清洗：{'、'.join(result.changes)}", dataset_id)
        lineage_svc.log(user_id, dataset_id, None, "clean", "table:data",
                        f"AI清洗：{'、'.join(result.changes)}",
                        {"row_count": result.rows_before, "columns_count": 0},
                        {"row_count": result.rows_after, "columns_count": 0})
        return success(data=result.model_dump())
    except Exception as e:
        return error(500, str(e))


@router.post("/{dataset_id}/undo")
def undo(dataset_id: str):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    versions = version_svc.list_versions(dataset_id)
    if not versions:
        return error(400, "没有可撤销的操作")
    latest = versions[0]  # Most recent version
    ok = version_svc.rollback(dataset_id, latest["id"], duckdb_dir=DUCKDB_DIR)
    if ok:
        return success(message=f"已撤销到 v{latest['version']}")
    return error(400, "回滚失败")
