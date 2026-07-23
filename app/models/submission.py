from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class SubmissionStatus(str, Enum):
    pending = "pending"
    running = "running"
    finished = "finished"
    failed = "failed"

class JudgeResult(str, Enum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    SE = "SE"
    RE = "RE"

class SubmissionCreateRequest(BaseModel):
    problem_id: str
    language: str = "python"
    source_code: str = Field(min_length = 1)

class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    problem_id: str
    language: str
    source_code: Optional[str] = None
    status: SubmissionStatus
    result: Optional[JudgeResult] = None
    score: int
    total_time: Optional[float] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class SubmissionListItem(BaseModel):
    id: str
    user_id: str
    problem_id: str
    language: str
    status: SubmissionStatus
    result: Optional[JudgeResult] = None
    score: int
    total_time: Optional[float] = None
    created_at: str