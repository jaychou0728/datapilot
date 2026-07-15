from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.service.metadata_service import MetadataService
from app.utils.response import success, error

router = APIRouter(prefix="/api/metadata", tags=["metadata"])
svc = MetadataService()


class SaveMetadataRequest(BaseModel):
    dataset_id: str
    column_name: str
    label: str = ""
    unit: str = ""
    description: str = ""


@router.get("/{dataset_id}")
def get_metadata(dataset_id: str):
    return success(data=svc.get(dataset_id))


@router.put("")
def save_metadata(req: SaveMetadataRequest):
    svc.save(req.dataset_id, req.column_name, req.label, req.unit, req.description)
    return success(message="已保存")


@router.delete("/{dataset_id}/{column_name}")
def delete_column_meta(dataset_id: str, column_name: str, user: dict = Depends(get_current_user)):
    svc.delete_column(dataset_id, column_name)
    return success(message="已删除")
