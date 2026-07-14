from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.service.lineage_service import LineageService
from app.utils.response import success

router = APIRouter(prefix="/api/lineage", tags=["lineage"])
lineage_svc = LineageService()

@router.get("/{dataset_id}")
def get_chain(dataset_id: str):
    chain = lineage_svc.get_chain(dataset_id)
    return success(data=chain)

@router.get("/{dataset_id}/graph")
def get_graph(dataset_id: str):
    graph = lineage_svc.get_graph(dataset_id)
    return success(data=graph)
