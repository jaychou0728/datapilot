from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.service.task_service import TaskService
from app.utils.response import success, error

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
task_svc = TaskService()

@router.get("")
def list_tasks(user: dict = Depends(get_current_user)):
    return success(data=task_svc.list_by_user(user["id"]))

@router.get("/{task_id}")
def get_task(task_id: str):
    task = task_svc.get(task_id)
    if not task:
        return error(404, "任务不存在")
    return success(data=task)

@router.delete("/{task_id}")
def delete_task(task_id: str):
    task_svc.delete(task_id)
    return success(message="已删除")
