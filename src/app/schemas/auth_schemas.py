from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterUserInput(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    password_confirmation: str = Field(min_length=8, max_length=256)


class RoleBrief(BaseModel):
    id: UUID
    name: str


class UserProfileOutput(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    middle_name: str | None
    role: RoleBrief
    is_active: bool
    created_at: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class LoginOutput(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_in: int
    session_id: UUID
    user: UserProfileOutput


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshOutput(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_in: int
    session_id: UUID


class LogoutInput(BaseModel):
    access_token: str
    session_id: UUID
    user_id: UUID


class AccessTokenInput(BaseModel):
    access_token: str
    session_id: UUID
    user_id: UUID


class AuthenticatedPrincipal(BaseModel):
    user_id: UUID
    session_id: UUID
    role_id: UUID
    role_name: str
