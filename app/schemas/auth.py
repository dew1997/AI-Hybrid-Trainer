import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    weight_kg: float | None = Field(default=None, ge=30, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    primary_goal: str | None = Field(default=None, pattern="^(marathon|strength|fat_loss|general)$")
    experience_level: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    weekly_hours_target: float | None = Field(default=None, ge=1, le=40)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    primary_goal: str | None
    experience_level: str | None
    weight_kg: float | None
    max_hr: int | None
    vo2max_estimate: float | None

    model_config = {"from_attributes": True}


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    weight_kg: float | None = Field(default=None, ge=30, le=300)
    height_cm: float | None = Field(default=None, ge=100, le=250)
    resting_hr: int | None = Field(default=None, ge=30, le=100)
    max_hr: int | None = Field(default=None, ge=140, le=220)
    ftp_watts: int | None = Field(default=None, ge=50, le=500)
    vo2max_estimate: float | None = Field(default=None, ge=20, le=90)
    primary_goal: str | None = Field(default=None, pattern="^(marathon|strength|fat_loss|general)$")
    experience_level: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    weekly_hours_target: float | None = Field(default=None, ge=1, le=40)
