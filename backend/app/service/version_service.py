"""Dataset Versioning — snapshot DuckDB before mutations, support rollback & diff."""
import os
import shutil
import uuid
from datetime import datetime
from app.database import get_db
from app.data.duckdb_manager import DuckDBManager


VERSION_DIR = "versions"


class VersionService:

    def create(self, dataset_id: str, label: str = "", db_path: str = "",
               duckdb_dir: str = "duckdb_data") -> dict | None:
        """Snapshot the current DuckDB file as a new version."""
        src = db_path or os.path.join(duckdb_dir, f"{dataset_id}.duckdb")
        if not os.path.exists(src):
            return None

        conn = get_db()
        latest = conn.execute(
            "SELECT MAX(version) FROM dataset_versions WHERE dataset_id = ?",
            (dataset_id,),
        ).fetchone()[0]
        version_num = (latest or 0) + 1

        # Count rows and columns BEFORE copy (no lock issue since no copy yet)
        mgr = DuckDBManager(src)
        row_count = mgr.query("SELECT COUNT(*) AS cnt FROM data")[0]["cnt"]
        cols = mgr.get_columns("data")
        mgr.close()

        # Copy DuckDB file (now mgr connection is closed)
        ver_dir = os.path.join(duckdb_dir, VERSION_DIR, dataset_id)
        os.makedirs(ver_dir, exist_ok=True)
        dst = os.path.join(ver_dir, f"v{version_num}.duckdb")
        shutil.copy2(src, dst)

        ver_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO dataset_versions (id, dataset_id, version, label, row_count, column_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ver_id, dataset_id, version_num, label, row_count, len(cols)),
        )
        conn.commit()
        conn.close()
        return {"id": ver_id, "version": version_num, "row_count": row_count,
                "column_count": len(cols), "label": label,
                "created_at": datetime.now().isoformat()}

    def list_versions(self, dataset_id: str) -> list[dict]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM dataset_versions WHERE dataset_id = ? ORDER BY version DESC",
            (dataset_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def rollback(self, dataset_id: str, version_id: str,
                 duckdb_dir: str = "duckdb_data") -> bool:
        """Restore a previous version as the current data."""
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM dataset_versions WHERE id = ? AND dataset_id = ?",
            (version_id, dataset_id),
        ).fetchone()
        if not row:
            conn.close()
            return False

        ver = dict(row)
        src = os.path.join(duckdb_dir, VERSION_DIR, dataset_id,
                          f"v{ver['version']}.duckdb")
        dst = os.path.join(duckdb_dir, f"{dataset_id}.duckdb")

        if not os.path.exists(src):
            conn.close()
            return False

        conn.close()
        # Copy the version file back to the current data file
        shutil.copy2(src, dst)
        return True

    def diff(self, dataset_id: str, v1_id: str, v2_id: str,
             duckdb_dir: str = "duckdb_data") -> dict:
        """Compare two versions: row/column changes."""
        conn = get_db()
        r1 = conn.execute(
            "SELECT * FROM dataset_versions WHERE id = ?", (v1_id,)
        ).fetchone()
        r2 = conn.execute(
            "SELECT * FROM dataset_versions WHERE id = ?", (v2_id,)
        ).fetchone()
        conn.close()
        if not r1 or not r2:
            return {}

        v1, v2 = dict(r1), dict(r2)
        return {
            "v1": {"version": v1["version"], "row_count": v1["row_count"],
                   "column_count": v1["column_count"], "label": v1["label"]},
            "v2": {"version": v2["version"], "row_count": v2["row_count"],
                   "column_count": v2["column_count"], "label": v2["label"]},
            "row_delta": v2["row_count"] - v1["row_count"],
            "column_delta": v2["column_count"] - v1["column_count"],
        }

    def delete_dataset(self, dataset_id: str, duckdb_dir: str = "duckdb_data"):
        """Clean up all versions for a dataset."""
        ver_dir = os.path.join(duckdb_dir, VERSION_DIR, dataset_id)
        if os.path.exists(ver_dir):
            shutil.rmtree(ver_dir)
        conn = get_db()
        conn.execute("DELETE FROM dataset_versions WHERE dataset_id = ?", (dataset_id,))
        conn.commit()
        conn.close()
