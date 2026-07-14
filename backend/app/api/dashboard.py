from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.utils.response import success
from app.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
async def stats(user: dict = Depends(get_current_user)):
    conn = get_db()
    is_admin = user["role"] == "admin"
    uid = user["id"]

    if is_admin:
        total_ops = conn.execute("SELECT COUNT(*) FROM operation_logs").fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        recent = conn.execute(
            "SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
    else:
        total_ops = conn.execute("SELECT COUNT(*) FROM operation_logs WHERE user_id = ?", (uid,)).fetchone()[0]
        reports = conn.execute("SELECT COUNT(*) FROM reports WHERE user_id = ?", (uid,)).fetchone()[0]
        recent = conn.execute(
            "SELECT * FROM operation_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (uid,)
        ).fetchall()
    conn.close()
    activities = [{"type": r["type"], "detail": r["detail"], "time": r["created_at"], "id": r["id"]} for r in recent]
    return success(data={"operations_count": total_ops, "reports_count": reports, "recent_activities": activities})
