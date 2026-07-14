import io
import os
import csv
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from app.service.dataset_service import DatasetService
from app.service.history_service import HistoryService
from app.service.lineage_service import LineageService
from app.data.file_store import FileStore
from app.data.duckdb_manager import DuckDBManager
from app.config import UPLOAD_DIR, DUCKDB_DIR, MAX_FILE_SIZE_MB
from app.middleware.auth import get_current_user_id, get_current_user
from app.utils.response import success, error

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
file_store = FileStore(UPLOAD_DIR)
hist_svc = HistoryService()
lineage_svc = LineageService()


def get_service():
    return DatasetService(file_store=file_store, duckdb_dir=DUCKDB_DIR)


@router.post("/upload")
async def upload(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)):
    if not file.filename:
        return error(400, "文件名不能为空")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("xlsx", "xls", "csv"):
        return error(400, f"不支持的文件格式: .{ext}，仅支持 .xlsx .xls .csv")

    content = await file.read()
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        return error(400, f"文件大小不能超过 {MAX_FILE_SIZE_MB}MB")

    try:
        svc = get_service()
        info = svc.ingest(file.filename, content, user_id=user_id)
        hist_svc.log(user_id, "upload", f"上传了 {file.filename}（{info.rows} 行）", info.id)
        lineage_svc.log(user_id, info.id, None, "upload", "table:data",
                        f"上传 {file.filename} ({info.rows}行, {info.columns}列)",
                        {}, {"row_count": info.rows, "columns": info.columns})
        return success(data=info.model_dump(mode="json"))
    except Exception as e:
        return error(500, str(e))


@router.get("")
def list_datasets(user: dict = Depends(get_current_user)):
    svc = get_service()
    datasets = svc.list_all(user_id=user["id"], is_admin=user["role"] == "admin")
    return success(data=datasets)


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str):
    svc = get_service()
    info = svc.get_info(dataset_id)
    if info is None:
        return error(404, "数据集不存在")
    return success(data=info)


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str, user: dict = Depends(get_current_user)):
    svc = get_service()
    if svc.get_info(dataset_id) is None:
        return error(404, "数据集不存在")
    if user["role"] != "admin" and not svc.is_owner(dataset_id, user["id"]):
        return error(403, "无权限删除此数据集")
    svc.delete(dataset_id)
    return success(message="已删除")


@router.get("/{dataset_id}/preview")
def preview(dataset_id: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    svc = get_service()
    if svc.get_info(dataset_id) is None:
        return error(404, "数据集不存在")
    try:
        result = svc.preview(dataset_id, page, page_size)
        return success(data=result)
    except Exception as e:
        return error(500, str(e))


@router.get("/{dataset_id}/export")
def export_csv(dataset_id: str):
    svc = get_service()
    info = svc.get_info(dataset_id)
    if info is None:
        return error(404, "数据集不存在")

    db_path = os.path.join(DUCKDB_DIR, f"{dataset_id}.duckdb")
    mgr = DuckDBManager(db_path)
    rows = mgr.query("SELECT * FROM data", limit=1000000)
    columns = mgr.get_columns("data")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])

    output.seek(0)
    filename = info["name"].rsplit(".", 1)[0] + "_cleaned.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
