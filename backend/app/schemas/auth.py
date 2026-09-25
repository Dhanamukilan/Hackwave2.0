from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime
from backend.app.models.base import UserRole

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.DEVELOPER

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    must_change_password: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
