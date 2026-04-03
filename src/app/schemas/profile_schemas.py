from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth_schemas import UserProfileOutput


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None


class CurrentUserInput(BaseModel):
    user_id: UUID
    session_id: UUID
    role_id: UUID
    role_name: str


class UpdateProfileInput(BaseModel):
    user_id: UUID
    session_id: UUID
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
