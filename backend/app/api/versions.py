from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.service.version_service import VersionService
from app.config import DUCKDB_DIR
from app.utils.response import success, error
import os

router = APIRouter(prefix="/api/versions", tags=["versions"])
svc = VersionService()


class RollbackRequest(BaseModel):
    dataset_id: str
    version_id: str


@router.get("/{dataset_id}")
def list_versions(dataset_id: str):
    return success(data=svc.list_versions(dataset_id))


@router.post("/snapshot/{dataset_id}")
def create_snapshot_manual(dataset_id: str, user: dict = Depends(get_current_user)):
    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    if not os.path.exists(db_path):
        return error(404, "数据集不存在")
    ver = svc.create(dataset_id, db_path=db_path, duckdb_dir=DUCKDB_DIR)
    if not ver:
        return error(500, "创建快照失败")
    return success(data=ver)


@router.post("/rollback")
def rollback(req: RollbackRequest, user: dict = Depends(get_current_user)):
    ok = svc.rollback(req.dataset_id, req.version_id, duckdb_dir=DUCKDB_DIR)
    if not ok:
        return error(400, "版本不存在或文件丢失")
    return success(message="已回滚")


@router.get("/diff/{dataset_id}")
def diff_versions(dataset_id: str, v1: str, v2: str):
    result = svc.diff(dataset_id, v1, v2, duckdb_dir=DUCKDB_DIR)
    return success(data=result)
