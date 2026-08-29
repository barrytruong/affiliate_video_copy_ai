from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    INGESTING = "ingesting"
    TRANSCRIBING = "transcribing"
    WRITING = "writing"
    DONE = "done"
    ERROR = "error"


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    language: str
    language_probability: float
    duration: float
    segments: list[TranscriptSegment]
    full_text: str


@dataclass
class Job:
    id: str
    source_type: Literal["url", "upload"]
    source: str
    target_language: Literal["en", "vi"] = "en"
    status: JobStatus = JobStatus.PENDING
    stage_message: str = "Đang chờ xử lý..."
    transcript: TranscriptResult | None = None
    script: str | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class JobCreateResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    stage_message: str
    script: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    ollama_ok: bool
    model_ok: bool
    ollama_model: str
    whisper_device: str
    detail: str | None = None
