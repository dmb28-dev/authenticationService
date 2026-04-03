from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class MockDocumentOutput(BaseModel):
    id: str
    title: str
    owner_id: UUID
    status: str
    created_at: str


class MockDocumentListOutput(BaseModel):
    items: list[MockDocumentOutput]


class MockReportOutput(BaseModel):
    id: str
    title: str
    owner_id: UUID
    summary: str | None
    created_at: str


class MockReportListOutput(BaseModel):
    items: list[MockReportOutput]


class CreateDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=512)


class UpdateDocumentRequest(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    status: str | None = Field(default=None, max_length=64)


class ListDocumentsInput(BaseModel):
    user_id: UUID
    role_id: UUID
    limit: int = 50
    offset: int = 0


class GetDocumentInput(BaseModel):
    user_id: UUID
    role_id: UUID
    document_id: str


class CreateDocumentInput(BaseModel):
    user_id: UUID
    role_id: UUID
    title: str = Field(min_length=1, max_length=512)


class UpdateDocumentInput(BaseModel):
    user_id: UUID
    role_id: UUID
    document_id: str
    title: str | None = None
    status: str | None = None


class DeleteDocumentInput(BaseModel):
    user_id: UUID
    role_id: UUID
    document_id: str


class ListReportsInput(BaseModel):
    user_id: UUID
    role_id: UUID
    limit: int = 50
    offset: int = 0
