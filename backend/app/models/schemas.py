"""Validated request and response shapes shared by the API."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.core.config import settings


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuthRequest(APIModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value


class UserResponse(APIModel):
    id: str
    email: str
    created_at: str


class DocumentResponse(APIModel):
    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: Literal["processing", "ready", "failed"]
    chunk_count: int
    created_at: str
    error_message: str | None = None


class DocumentListResponse(APIModel):
    documents: list[DocumentResponse]
    total: int


class SourceCitation(APIModel):
    citation_id: str
    document_id: str
    document: str
    page: int | None = None
    chunk_index: int | None = None
    text: str
    relevance_score: float


class QueryRequest(APIModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=settings.default_top_k, ge=1, le=settings.max_top_k)
    document_ids: list[str] | None = Field(default=None, max_length=100)
    conversation_id: str | None = None

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Enter a question with at least two characters.")
        return value


class QueryResponse(APIModel):
    answer: str
    sources: list[SourceCitation]
    conversation_id: str | None = None
    generation_mode: Literal["llm", "extractive", "insufficient_context"]
    warning: str | None = None
    latency_ms: int
    retrieved_count: int


class ChatRequest(QueryRequest):
    conversation_id: str | None = None


class ChatMessage(APIModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceCitation] = Field(default_factory=list)
    created_at: str


class ConversationSummary(APIModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationDetail(ConversationSummary):
    messages: list[ChatMessage]


class RetrievalEvaluationRequest(APIModel):
    relevant_ids: list[str]
    retrieved_ids: list[str]
    k: int = Field(default=5, ge=1, le=100)


class RetrievalEvaluationResponse(APIModel):
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float


class GenerationEvaluationRequest(APIModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)
    context: str = Field(default="", max_length=50000)
    expected_answer: str | None = Field(default=None, max_length=10000)
    cited_ids: list[str] = Field(default_factory=list, max_length=100)
    available_ids: list[str] = Field(default_factory=list, max_length=100)


class GenerationEvaluationResponse(APIModel):
    faithfulness_proxy: float
    context_relevance: float
    answer_relevance: float
    citation_correctness: float
    heuristic_metrics: bool


class HealthResponse(APIModel):
    status: Literal["ok"]
    service: str
    llm_configured: bool
    embedding_model: str
