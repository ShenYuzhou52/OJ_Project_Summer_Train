#审计日志模型，用来打各种log
from pydantic import BaseModel
from typing import Optional

class AuditLogResponse(BaseModel):
    id: str
    operator_id: str
    action: str
    target_type: Optional[str] = None #problem，submission，user
    target_id: Optional[str] = None
    success: bool #操作成功与否
    detail: Optional[str] = None
    created_at: str