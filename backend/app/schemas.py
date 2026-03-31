import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr

from app.db.models import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: Role
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class AnalysisStatsOut(BaseModel):
    total_checks: int
    total_defects: int
    avg_confidence: float
    no_defect_photos: int
    by_type: dict[str, int]


class AnalysisOut(BaseModel):
    id: uuid.UUID
    filename: str
    result: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisListOut(BaseModel):
    items: list[AnalysisOut]
    total: int
