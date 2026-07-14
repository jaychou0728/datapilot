import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
DUCKDB_DIR = os.getenv("DUCKDB_DIR", "duckdb_data")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "7"))
JWT_SECRET = os.getenv("JWT_SECRET", "datapilot-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "default-user")
SQLITE_DB = os.getenv("SQLITE_DB", "data.db")
