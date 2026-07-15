from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.cleaning import router as cleaning_router
from app.api.query import router as query_router
from app.api.charts import router as charts_router
from app.api.chat import router as chat_router
from app.api.dashboard import router as dashboard_router
from app.api.history import router as history_router
from app.api.reports import router as reports_router
from app.api.tasks import router as tasks_router
from app.api.agent import router as agent_router
from app.api.lineage import router as lineage_router
from app.api.metadata import router as metadata_router
from app.api.versions import router as versions_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(cleaning_router)
api_router.include_router(query_router)
api_router.include_router(charts_router)
api_router.include_router(chat_router)
api_router.include_router(dashboard_router)
api_router.include_router(history_router)
api_router.include_router(reports_router)
api_router.include_router(tasks_router)
api_router.include_router(agent_router)
api_router.include_router(lineage_router)
api_router.include_router(metadata_router)
api_router.include_router(versions_router)
