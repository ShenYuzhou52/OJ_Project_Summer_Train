from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    code: int
    message: str
    data: Optional[T] = None

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

def success(data: Any = None, message: str = 'ok', code: int = 200) -> dict:
    return {"code": code, "message": message, "data": data}

def created(data: Any = None, message: str = 'created') -> dict:
    return {"code": 201, "message":message, "data":data}

def accepted(data: Any = None, message: str = 'accepted') -> dict:
    return {"code": 202, "message":message, "data": data}

def error(code: int, message: str) -> dict:
    return {"code": code,"message":message, "data":None}