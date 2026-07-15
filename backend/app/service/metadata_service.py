"""Semantic Layer — column-level metadata for better AI understanding."""
from app.database import get_db


class MetadataService:

    def save(self, dataset_id: str, column_name: str, label: str = "",
             unit: str = "", description: str = ""):
        conn = get_db()
        conn.execute(
            """INSERT OR REPLACE INTO column_metadata (dataset_id, column_name, label, unit, description)
               VALUES (?, ?, ?, ?, ?)""",
            (dataset_id, column_name, label, unit, description),
        )
        conn.commit()
        conn.close()

    def get(self, dataset_id: str) -> dict[str, dict]:
        """Return {column_name: {label, unit, description}} for all columns."""
        conn = get_db()
        rows = conn.execute(
            "SELECT column_name, label, unit, description FROM column_metadata WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchall()
        conn.close()
        return {
            r["column_name"]: {"label": r["label"], "unit": r["unit"],
                               "description": r["description"]}
            for r in rows
        }

    def build_context(self, dataset_id: str, column_name: str) -> str:
        """Build a short natural-language description for a single column."""
        meta = self.get(dataset_id).get(column_name, {})
        label = meta.get("label", "")
        unit = meta.get("unit", "")
        desc = meta.get("description", "")
        if not label and not unit and not desc:
            return ""
        parts = []
        if label:
            parts.append(f'含义: {label}')
        if unit:
            parts.append(f'单位: {unit}')
        if desc:
            parts.append(f'说明: {desc}')
        return "（" + "，".join(parts) + "）"

    def build_all_hints(self, dataset_id: str) -> str:
        """Build a compact hint string for all columns, for prompt injection."""
        meta = self.get(dataset_id)
        if not meta:
            return ""
        lines = ["## 列语义说明"]
        for col, m in meta.items():
            parts = []
            if m["label"]:
                parts.append(m["label"])
            if m["unit"]:
                parts.append(f"({m["unit"]})")
            if m["description"]:
                parts.append(f"— {m["description"]}")
            if parts:
                lines.append(f"- {col}: {' '.join(parts)}")
        return "\n".join(lines) if len(lines) > 1 else ""

    def delete_column(self, dataset_id: str, column_name: str):
        conn = get_db()
        conn.execute(
            "DELETE FROM column_metadata WHERE dataset_id = ? AND column_name = ?",
            (dataset_id, column_name),
        )
        conn.commit()
        conn.close()

    def delete_dataset(self, dataset_id: str):
        conn = get_db()
        conn.execute("DELETE FROM column_metadata WHERE dataset_id = ?", (dataset_id,))
        conn.commit()
        conn.close()
