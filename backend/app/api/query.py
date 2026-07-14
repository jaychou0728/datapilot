from fastapi import APIRouter, Depends
from app.service.query_service import QueryService
from app.service.history_service import HistoryService
from app.config import DUCKDB_DIR
from app.middleware.auth import get_current_user_id
from app.utils.response import success, error
from app.model.query import QueryRequest

router = APIRouter(prefix="/api/query", tags=["query"])
hist_svc = HistoryService()


@router.post("/execute")
def execute_query(req: QueryRequest, user_id: str = Depends(get_current_user_id)):
    svc = QueryService(duckdb_dir=DUCKDB_DIR)
    try:
        result = svc.execute(
            dataset_id=req.dataset_id,
            sql=req.sql,
            natural_language=req.natural_language,
        )
        detail = req.natural_language or (req.sql[:80] if req.sql else "查询")
        hist_svc.log(user_id, "query", f"查询：{detail}", req.dataset_id)
        return success(data=result.model_dump())
    except FileNotFoundError:
        return error(404, "数据集不存在")
    except ValueError as e:
        return error(400, str(e))
    except Exception as e:
        return error(500, str(e))
