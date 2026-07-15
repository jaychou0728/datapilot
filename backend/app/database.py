import sqlite3
from app.config import SQLITE_DB

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS operation_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            detail TEXT NOT NULL,
            dataset_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS task_queue (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            input JSON,
            output JSON,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS data_lineage (
            id TEXT PRIMARY KEY,
            task_id TEXT,
            user_id TEXT NOT NULL,
            dataset_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            target TEXT NOT NULL,
            summary TEXT NOT NULL,
            before_snapshot TEXT,
            after_snapshot TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS dataset_owners (
            dataset_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS column_metadata (
            dataset_id TEXT NOT NULL,
            column_name TEXT NOT NULL,
            label TEXT DEFAULT '',
            unit TEXT DEFAULT '',
            description TEXT DEFAULT '',
            PRIMARY KEY (dataset_id, column_name)
        );
        CREATE TABLE IF NOT EXISTS dataset_versions (
            id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            label TEXT DEFAULT '',
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    try:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
