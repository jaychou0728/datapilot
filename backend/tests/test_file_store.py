import pytest
from app.data.file_store import FileStore

def test_save_and_get(tmp_path):
    store = FileStore(str(tmp_path))
    content = b"fake file content"
    store.save("abc-123", "sales.xlsx", content)
    saved = store.get_path("abc-123")
    assert saved.exists()
    assert (saved / "sales.xlsx").read_bytes() == content

def test_delete_dataset(tmp_path):
    store = FileStore(str(tmp_path))
    store.save("abc-123", "test.csv", b"data")
    store.delete("abc-123")
    assert not store.get_path("abc-123").exists()

def test_cleanup_old_files(tmp_path):
    import time, os
    store = FileStore(str(tmp_path))
    store.save("old-ds", "f.csv", b"x")
    old_dir = store.get_path("old-ds")
    os.utime(old_dir, (time.time() - 8*86400, time.time() - 8*86400))
    store.cleanup(retention_days=7)
    assert not old_dir.exists()
