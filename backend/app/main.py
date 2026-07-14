import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.data.file_store import FileStore
from app.config import UPLOAD_DIR, DUCKDB_DIR, DATA_RETENTION_DAYS
from app.utils.response import error

app = FastAPI(title="DataPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.on_event("startup")
async def startup():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(DUCKDB_DIR, exist_ok=True)
    from app.database import init_db
    init_db()
    file_store = FileStore(UPLOAD_DIR)
    file_store.cleanup(DATA_RETENTION_DAYS)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=error(500, f"服务器内部错误: {str(exc)}"),
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}
