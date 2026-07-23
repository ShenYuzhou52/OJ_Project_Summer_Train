import os
import sys
import asyncio

# Windows: 确保使用 ProactorEventLoop（支持 subprocess）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 修复 Windows 控制台中文乱码
if sys.platform == "win32":
    os.system("")  # 启用 ANSI 转义序列
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse, JSONResponse
from app.config import SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, BASE_DIR
from app.repositories.database import init_db
from app.repositories.user_repo import get_user_by_username, create_user
from app.routers import auth, problems, submissions, logs, audit_logs, admin, similarity

app = FastAPI(title="OJ System", version="1.0.0")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)
app.include_router(logs.router)
app.include_router(audit_logs.router)
app.include_router(admin.router)
app.include_router(similarity.router)


# 静态文件服务
frontend_dir = os.path.join(BASE_DIR, "frontend")
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))


# 统一异常处理：将 HTTPException 转为统一响应格式
from fastapi import HTTPException

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = "; ".join(
        f"{'.'.join(str(l) for l in e['loc'][1:])}: {e['msg']}" for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": errors, "data": None},
    )


@app.on_event("startup")
async def startup():
    await init_db()
    existing = await get_user_by_username(ADMIN_USERNAME)
    if not existing:
        import bcrypt as _bcrypt
        hashed = _bcrypt.hashpw(ADMIN_PASSWORD.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")
        await create_user(ADMIN_USERNAME, hashed, role="admin")
        print(f"admin account created: {ADMIN_USERNAME}")