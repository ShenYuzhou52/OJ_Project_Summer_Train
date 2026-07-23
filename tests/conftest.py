import pytest
import os

# 使用测试专用配置
os.environ["OJ_SECRET_KEY"] = "test-secret-key"
os.environ["OJ_ADMIN_USERNAME"] = "admin"
os.environ["OJ_ADMIN_PASSWORD"] = "admin123456"

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.repositories.database import init_db, get_db
from app.repositories.user_repo import get_user_by_username, create_user

# pytest-asyncio auto mode
pytest_plugins = ['pytest_asyncio']


@pytest.fixture
async def client(tmp_path):
    """每个测试使用独立数据库，client fixture 本身是 async 的，确保 init_db 在同一事件循环"""
    import app.config as cfg
    cfg.DB_PATH = str(tmp_path / "test_oj.db")
    cfg.BACKUP_DIR = str(tmp_path / "backups")
    cfg.TEMP_DIR = str(tmp_path / "temp")
    os.makedirs(cfg.BACKUP_DIR, exist_ok=True)
    os.makedirs(cfg.TEMP_DIR, exist_ok=True)

    # 初始化数据库并创建 admin 用户
    await init_db()
    existing = await get_user_by_username("admin")
    if not existing:
        import bcrypt as _bcrypt
        hashed = _bcrypt.hashpw(b"admin123456", _bcrypt.gensalt()).decode("utf-8")
        await create_user("admin", hashed, role="admin")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client(client: AsyncClient):
    """已登录 admin 的 client"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    return client


@pytest.fixture
async def student_client(client: AsyncClient):
    """已登录 student 的 client"""
    await client.post("/api/auth/register", json={"username": "teststudent", "password": "teststudent1"})
    await client.post("/api/auth/login", json={"username": "teststudent", "password": "teststudent1"})
    return client


SAMPLE_PROBLEM = {
    "id": "test-prob-01",
    "title": "A+B Problem",
    "description": "计算两个整数的和",
    "input_description": "两个整数 a b",
    "output_description": "输出 a+b",
    "samples": [{"input": "1 2", "output": "3"}],
    "constraints": "1<=a,b<=1000",
    "time_limit": 2.0,
    "memory_limit": 256.0,
    "difficulty": "easy",
    "tags": ["math"],
    "test_cases": [
        {"case_id": "tc1", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
        {"case_id": "tc2", "input": "3 4\n", "output": "7\n", "score": 50, "is_hidden": True},
    ],
}