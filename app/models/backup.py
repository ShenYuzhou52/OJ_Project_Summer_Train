from pydantic import BaseModel

class BackupResponse(BaseModel):
    backup_id: str
    created_at: str

