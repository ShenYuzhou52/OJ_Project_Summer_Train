#单条测试点判题日志的model
from pydantic import BaseModel
from typing import Optional
from app.models.submission import JudgeResult

class JudgeLogResponse(BaseModel):
    submission_id: str
    case_id: str
    result: JudgeResult
    score: int
    time_used: float
    memory_used: Optional[float] = None
    exit_code: int 
    input_data: Optional[str] = None #学生不可见
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    expected_output: Optional[str] = None
    message: Optional[str] = None
    is_hidden: Optional[bool] = None
    created_at: str
