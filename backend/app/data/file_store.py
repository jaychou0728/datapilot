import shutil
import time
import os
from pathlib import Path

class FileStore:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, dataset_id: str, filename: str, content: bytes) -> Path:
        ds_dir = self.base_dir / dataset_id
        ds_dir.mkdir(parents=True, exist_ok=True)
        file_path = ds_dir / filename
        file_path.write_bytes(content)
        return ds_dir

    def get_path(self, dataset_id: str) -> Path:
        return self.base_dir / dataset_id

    def delete(self, dataset_id: str):
        ds_dir = self.base_dir / dataset_id
        if ds_dir.exists():
            shutil.rmtree(ds_dir)

    def cleanup(self, retention_days: int = 7):
        now = time.time()
        cutoff = now - retention_days * 86400
        for ds_dir in self.base_dir.iterdir():
            if ds_dir.is_dir():
                mtime = os.path.getmtime(ds_dir)
                if mtime < cutoff:
                    shutil.rmtree(ds_dir)
