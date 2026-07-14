from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from app.middleware.auth import get_current_user
from app.service.agent_service import AgentService
from app.service.task_service import TaskService
from app.utils.response import success, error

router = APIRouter(prefix="/api/agent", tags=["agent"])

class AgentRunRequest(BaseModel):
    dataset_id: str

@router.post("/run")
async def run_agent(req: AgentRunRequest, background_tasks: BackgroundTasks,
                    user: dict = Depends(get_current_user)):
    task_svc = TaskService()
    task = task_svc.create(user["id"], "agent_pipeline", {"dataset_id": req.dataset_id})
    agent_svc = AgentService()
    background_tasks.add_task(agent_svc.run_pipeline, task["id"], user["id"], req.dataset_id)
    return success(data={"task_id": task["id"]})

@router.get("/result/{task_id}")
def get_result(task_id: str):
    task_svc = TaskService()
    task = task_svc.get(task_id)
    if not task:
        return error(404, "任务不存在")
    return success(data=task)
