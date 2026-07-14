import uuid
from app.database import get_db

class HistoryService:
    def log(self, user_id: str, type: str, detail: str, dataset_id: str | None = None):
        conn = get_db()
        conn.execute(
            "INSERT INTO operation_logs (id, user_id, type, detail, dataset_id) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, type, detail, dataset_id),
        )
        conn.commit()
        conn.close()

    def list_by_user(self, user_id: str, type_filter: str | None = None, limit: int = 50) -> list[dict]:
        conn = get_db()
        if type_filter:
            rows = conn.execute(
                "SELECT * FROM operation_logs WHERE user_id = ? AND type = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, type_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM operation_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def list_all(self, type_filter: str | None = None, limit: int = 50) -> list[dict]:
        conn = get_db()
        if type_filter:
            rows = conn.execute(
                "SELECT * FROM operation_logs WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                (type_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
