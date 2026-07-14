import pytest
import pandas as pd
from app.data.duckdb_manager import DuckDBManager

@pytest.fixture
def sample_df():
    return pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})

def test_create_and_query(tmp_path, sample_df):
    db_path = str(tmp_path / "test.duckdb")
    mgr = DuckDBManager(db_path)
    mgr.create_table(sample_df, "users")
    result = mgr.query("SELECT * FROM users ORDER BY age")
    assert len(result) == 2
    assert result[0]["name"] == "Bob"

def test_preview_with_pagination(tmp_path, sample_df):
    db_path = str(tmp_path / "test.duckdb")
    mgr = DuckDBManager(db_path)
    mgr.create_table(sample_df, "users")
    rows, total = mgr.preview("users", page=1, page_size=1)
    assert len(rows) == 1
    assert total == 2

def test_write_operation_blocked(tmp_path, sample_df):
    db_path = str(tmp_path / "test.duckdb")
    mgr = DuckDBManager(db_path)
    mgr.create_table(sample_df, "users")
    with pytest.raises(ValueError, match="不允许写操作"):
        mgr.query("INSERT INTO users VALUES ('X', 99)")

def test_get_table_info(tmp_path, sample_df):
    db_path = str(tmp_path / "test.duckdb")
    mgr = DuckDBManager(db_path)
    mgr.create_table(sample_df, "users")
    info = mgr.get_table_info("users")
    assert len(info) == 2
    assert info[0]["column_name"] == "name"
