from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: str
    services: dict[str, str]


class VideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    media_type: str
    status: str
    created_at: datetime


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    video_id: str
    kind: str
    status: str
    result: dict | None = None
    error: str | None = None


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalHit(BaseModel):
    document_id: str
    filename: str
    score: float
    excerpt: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    incident_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[RetrievalHit] = []
    evidence_sufficiency: Literal["insufficient", "limited", "sufficient"] = "insufficient"


class Report(BaseModel):
    incident_id: str
    summary: str
    incident_type: str | None = None
    event_timestamp: float | None = None
    model_observations: list[str] = []
    visual_evidence: list[str] = []
    potential_contributing_factors: list[str] = []
    supporting_documents: list[str] = []
    uncertainties: list[str] = []
    recommendations: list[str] = []
    evidence_sufficiency: Literal["insufficient", "limited", "sufficient"] = "insufficient"
    review_status: Literal["pending", "reviewed"] = "pending"


class LLMConfigRequest(BaseModel):
    provider: Literal["openai", "openrouter"]
    api_key: str = Field(min_length=10, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)


class LLMConfigOut(BaseModel):
    provider: str | None
    model: str | None
    configured: bool
    base_url: str | None
