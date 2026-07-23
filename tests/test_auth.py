"""用户权限测试：注册登录、角色权限、禁用用户、未登录访问"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# --- 注册和登录 ---
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "newuser", "password": "newuser12345"})
    assert resp.status_code == 201
    assert resp.json()["data"]["username"] == "newuser"
    assert resp.json()["data"]["role"] == "student"


async def test_register_duplicate(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "dupuser", "password": "dupuser12345"})
    resp = await client.post("/api/auth/register", json={"username": "dupuser", "password": "dupuser12345"})
    assert resp.status_code == 409


async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={"username": "shortpw", "password": "123"})
    assert resp.status_code == 422


async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "loginuser", "password": "loginuser123"})
    resp = await client.post("/api/auth/login", json={"username": "loginuser", "password": "loginuser123"})
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "loginuser"


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "wrongpw", "password": "wrongpw12345"})
    resp = await client.post("/api/auth/login", json={"username": "wrongpw", "password": "badpassword1"})
    assert resp.status_code == 401


async def test_logout(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "logout01", "password": "logout012345"})
    await client.post("/api/auth/login", json={"username": "logout01", "password": "logout012345"})
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 200


# --- 角色权限 ---
async def test_student_cannot_access_admin(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "stu_noadmin", "password": "stu_noadmin1"})
    await client.post("/api/auth/login", json={"username": "stu_noadmin", "password": "stu_noadmin1"})
    resp = await client.get("/api/users")
    assert resp.status_code == 403


async def test_student_cannot_create_problem(client: AsyncClient):
    from tests.conftest import SAMPLE_PROBLEM
    await client.post("/api/auth/register", json={"username": "stu_noprob", "password": "stu_noprob12"})
    await client.post("/api/auth/login", json={"username": "stu_noprob", "password": "stu_noprob12"})
    resp = await client.post("/api/problems", json=SAMPLE_PROBLEM)
    assert resp.status_code == 403


async def test_admin_can_access_users(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp = await client.get("/api/users")
    assert resp.status_code == 200


# --- 禁用用户 ---
async def test_disabled_user_cannot_login(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "disabled01", "password": "disabled0123"})
    # admin 登录并禁用
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp = await client.get("/api/users")
    users = resp.json()["data"]["items"]
    target = next(u for u in users if u["username"] == "disabled01")
    await client.put(f"/api/users/{target['id']}", json={"is_active": False})
    await client.post("/api/auth/logout")
    # 禁用用户尝试登录
    resp = await client.post("/api/auth/login", json={"username": "disabled01", "password": "disabled0123"})
    assert resp.status_code == 403


# --- 未登录访问 ---
async def test_unauthenticated_cannot_access_problems(client: AsyncClient):
    resp = await client.get("/api/problems")
    assert resp.status_code == 401


async def test_unauthenticated_cannot_submit(client: AsyncClient):
    resp = await client.post("/api/submissions", json={
        "problem_id": "xxx", "language": "python", "source_code": "print(1)"
    })
    assert resp.status_code == 401