import json
import uuid
from app.database import get_db

class LineageService:
    def log(self, user_id: str, dataset_id: str, task_id: str | None,
            operation: str, target: str, summary: str,
            before_snapshot: dict, after_snapshot: dict):
        conn = get_db()
        conn.execute(
            """INSERT INTO data_lineage (id, task_id, user_id, dataset_id, operation, target, summary, before_snapshot, after_snapshot)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                task_id,
                user_id,
                dataset_id,
                operation,
                target,
                summary,
                json.dumps(before_snapshot, ensure_ascii=False, default=str),
                json.dumps(after_snapshot, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()
        conn.close()

    def get_chain(self, dataset_id: str) -> list[dict]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM data_lineage WHERE dataset_id = ? ORDER BY created_at ASC",
            (dataset_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_graph(self, dataset_id: str) -> dict:
        chain = self.get_chain(dataset_id)
        nodes = []
        edges = []
        for i, step in enumerate(chain):
            nodes.append({
                "id": step["id"],
                "label": step["operation"],
                "summary": step["summary"],
                "step": i + 1,
            })
            if i > 0:
                edges.append({
                    "source": chain[i - 1]["id"],
                    "target": step["id"],
                })
        return {"nodes": nodes, "edges": edges}
