from fastapi.responses import JSONResponse
from app.models.common import success,created,accepted,error

def ok(data=None, message="ok", status_code=200):
    return JSONResponse(content=success(data,message,status_code),status_code=status_code)

def created_resp(data=None, message="created"):
    return JSONResponse(content=created(data,message),status_code=201)

def accepted_resp(data=None, message="accepted"):
    return JSONResponse(content=accepted(data,message),status_code=202)

def error_resp(code: int, message: str):
    return JSONResponse(content=error(code, message),status_code=code)
