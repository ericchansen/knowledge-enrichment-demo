"""Data models for the application."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class PipelineType(StrEnum):
    """Type of processing pipeline."""

    BASELINE = "baseline"
    ENHANCED = "enhanced"


class DocumentStatus(StrEnum):
    """Status of a document in the corpus."""

    UPLOADED = "uploaded"
    BASELINE_PROCESSING = "baseline_processing"
    BASELINE_COMPLETE = "baseline_complete"
    ENHANCED_PROCESSING = "enhanced_processing"
    ENHANCED_COMPLETE = "enhanced_complete"
    FAILED = "failed"


class Document(BaseModel):
    """A document in the corpus."""

    filename: str
    blob_url: str = ""
    status: DocumentStatus = DocumentStatus.UPLOADED
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    baseline_result: dict[str, Any] | None = None
    enhanced_result: dict[str, Any] | None = None


class CorpusInfo(BaseModel):
    """Summary info about the document corpus."""

    total_documents: int = 0
    baseline_indexed: int = 0
    enhanced_indexed: int = 0
    documents: list[Document] = Field(default_factory=list)


class AnalysisComparison(BaseModel):
    """Side-by-side comparison of baseline vs enhanced analysis."""

    filename: str
    baseline_markdown: str = ""
    enhanced_markdown: str = ""
    enhanced_fields: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """A message in a chat conversation."""

    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request to chat with an agent."""

    message: str
    pipeline_type: PipelineType = PipelineType.BASELINE


class ChatResponse(BaseModel):
    """Response from a chat agent."""

    message: str
    pipeline_type: PipelineType
    citations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineRequest(BaseModel):
    """Request to run a pipeline on the corpus."""

    pipeline_type: PipelineType = PipelineType.BASELINE


class PipelineStatus(BaseModel):
    """Status of a pipeline run."""

    pipeline_type: PipelineType
    status: str  # "running", "complete", "error"
    documents_processed: int = 0
    documents_total: int = 0
    message: str = ""


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"
