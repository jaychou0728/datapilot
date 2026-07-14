import json
import uuid
from datetime import datetime
from app.database import get_db

class TaskService:
    def create(self, user_id: str, type: str, input_data: dict) -> dict:
        task_id = str(uuid.uuid4())
        conn = get_db()
        conn.execute(
            """INSERT INTO task_queue (id, user_id, type, status, progress, input)
               VALUES (?, ?, ?, 'pending', 0, ?)""",
            (task_id, user_id, type, json.dumps(input_data, ensure_ascii=False, default=str)),
        )
        conn.commit()
        conn.close()
        return {"id": task_id, "status": "pending", "progress": 0}

    def update(self, task_id: str, status: str = None, progress: int = None,
               output: dict = None, error: str = None):
        conn = get_db()
        if status:
            conn.execute("UPDATE task_queue SET status = ? WHERE id = ?", (status, task_id))
        if progress is not None:
            conn.execute("UPDATE task_queue SET progress = ? WHERE id = ?", (progress, task_id))
        if output is not None:
            conn.execute("UPDATE task_queue SET output = ? WHERE id = ?",
                         (json.dumps(output, ensure_ascii=False, default=str), task_id))
        if error is not None:
            conn.execute("UPDATE task_queue SET error = ? WHERE id = ?", (error, task_id))
        if status in ("done", "failed"):
            conn.execute("UPDATE task_queue SET finished_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), task_id))
        conn.commit()
        conn.close()

    def get(self, task_id: str) -> dict | None:
        conn = get_db()
        row = conn.execute("SELECT * FROM task_queue WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        for field in ("input", "output"):
            try:
                d[field] = json.loads(d[field]) if d[field] else None
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    def list_by_user(self, user_id: str, limit: int = 20) -> list[dict]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM task_queue WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            for field in ("input", "output"):
                try:
                    d[field] = json.loads(d[field]) if d[field] else None
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(d)
        return results

    def delete(self, task_id: str):
        conn = get_db()
        conn.execute("DELETE FROM task_queue WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
