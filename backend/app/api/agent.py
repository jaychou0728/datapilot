import asyncio
import threading
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.service.agent_service import AgentService
from app.service.task_service import TaskService
from app.utils.response import success, error

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    dataset_id: str


def _run_pipeline_in_thread(task_id: str, user_id: str, dataset_id: str):
    """在独立线程中运行 async pipeline，自带 event loop。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        agent_svc = AgentService()
        loop.run_until_complete(agent_svc.run_pipeline(task_id, user_id, dataset_id))
    except Exception as e:
        task_svc = TaskService()
        task_svc.update(task_id, status="failed", error=str(e))
    finally:
        loop.close()


@router.post("/run")
async def run_agent(req: AgentRunRequest, user: dict = Depends(get_current_user)):
    task_svc = TaskService()
    task = task_svc.create(user["id"], "agent_pipeline", {"dataset_id": req.dataset_id})
    thread = threading.Thread(
        target=_run_pipeline_in_thread,
        args=(task["id"], user["id"], req.dataset_id),
        daemon=True,
    )
    thread.start()
    return success(data={"task_id": task["id"]})


@router.get("/result/{task_id}")
def get_result(task_id: str):
    task_svc = TaskService()
    task = task_svc.get(task_id)
    if not task:
        return error(404, "任务不存在")
    return success(data=task)
