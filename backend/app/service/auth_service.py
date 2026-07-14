import uuid
from datetime import datetime
from passlib.context import CryptContext
from jose import jwt
from app.database import get_db
from app.config import JWT_SECRET, JWT_ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def register(self, username: str, password: str) -> dict:
        if len(password) < 6:
            raise ValueError("密码至少6位")
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.close()
            raise ValueError("用户名已存在")
        user_id = str(uuid.uuid4())
        password_hash = pwd_context.hash(password)
        # First user is admin
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        role = "admin" if total == 0 else "user"
        conn.execute(
            "INSERT INTO users (id, username, password_hash, role) VALUES (?, ?, ?, ?)",
            (user_id, username, password_hash, role),
        )
        conn.commit()
        conn.close()
        return {"id": user_id, "username": username, "role": role, "created_at": datetime.now()}

    def login(self, username: str, password: str) -> dict:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        if not row or not pwd_context.verify(password, row["password_hash"]):
            raise ValueError("用户名或密码错误")
        return {"id": row["id"], "username": row["username"], "role": row["role"], "created_at": row["created_at"]}

    def create_token(self, user_id: str) -> str:
        payload = {"sub": user_id, "iat": datetime.utcnow()}
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def verify_token(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload.get("sub")
        except Exception:
            return None

    def get_user(self, user_id: str) -> dict | None:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        if not row:
            return None
        return {"id": row["id"], "username": row["username"], "role": row["role"], "created_at": row["created_at"]}
