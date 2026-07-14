from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    id: str
    username: str
    created_at: datetime

class AuthResponse(BaseModel):
    token: str
    user: UserInfo
