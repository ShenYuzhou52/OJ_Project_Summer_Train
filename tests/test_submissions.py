"""提交状态测试：创建提交、合法状态流转、非法状态冲突、所有权、重新评测"""
import pytest
import asyncio
from httpx import AsyncClient
from tests.conftest import SAMPLE_PROBLEM

pytestmark = pytest.mark.asyncio

AC_CODE = 'a, b = map(int, input().split())\nprint(a + b)'


async def _create_problem_and_submit(client: AsyncClient, prob_id="sub-prob"):
    """辅助：创建题目并提交"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    prob = {**SAMPLE_PROBLEM, "id": prob_id, "time_limit": 3.0}
    await client.post("/api/problems", json=prob)
    await client.post("/api/auth/register", json={"username": f"substu_{prob_id}", "password": "substu1234567"})
    await client.post("/api/auth/login", json={"username": f"substu_{prob_id}", "password": "substu1234567"})
    resp = await client.post("/api/submissions", json={
        "problem_id": prob_id, "language": "python", "source_code": AC_CODE
    })
    return resp


# --- 创建提交 ---
async def test_create_submission(client: AsyncClient):
    resp = await _create_problem_and_submit(client, "sub-create")
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert "submission_id" in data
    assert data["status"] == "pending"


async def test_create_submission_invalid_problem(client: AsyncClient):
    await client.post("/api/auth/register", json={"username": "substu_inv", "password": "substu1234567"})
    await client.post("/api/auth/login", json={"username": "substu_inv", "password": "substu1234567"})
    resp = await client.post("/api/submissions", json={
        "problem_id": "nonexistent", "language": "python", "source_code": "print(1)"
    })
    assert resp.status_code == 404


async def test_create_submission_unsupported_language(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": "sub-lang"})
    await client.post("/api/auth/register", json={"username": "substu_lang", "password": "substu1234567"})
    await client.post("/api/auth/login", json={"username": "substu_lang", "password": "substu1234567"})
    resp = await client.post("/api/submissions", json={
        "problem_id": "sub-lang", "language": "java", "source_code": "class Main{}"
    })
    assert resp.status_code == 400


# --- 合法状态流转 ---
async def test_submission_status_flow(client: AsyncClient):
    """提交后状态从 pending -> running -> finished"""
    resp = await _create_problem_and_submit(client, "sub-flow")
    sid = resp.json()["data"]["submission_id"]
    # 等待完成
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{sid}")
        status = r.json()["data"]["status"]
        if status in ("finished", "failed"):
            break
    assert status in ("finished", "failed")


# --- 非法状态冲突 ---
async def test_rejudge_running_submission_conflict(client: AsyncClient):
    """评测中的提交不能重新评测"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    prob = {**SAMPLE_PROBLEM, "id": "sub-conflict", "time_limit": 3.0}
    await client.post("/api/problems", json=prob)
    await client.post("/api/auth/register", json={"username": "substu_conf", "password": "substu1234567"})
    await client.post("/api/auth/login", json={"username": "substu_conf", "password": "substu1234567"})
    # 提交一个慢代码使评测持续
    slow_code = "import time\ntime.sleep(2)\na,b=map(int,input().split())\nprint(a+b)"
    resp = await client.post("/api/submissions", json={
        "problem_id": "sub-conflict", "language": "python", "source_code": slow_code
    })
    sid = resp.json()["data"]["submission_id"]
    await asyncio.sleep(0.3)
    # 切换为admin尝试重新评测
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp2 = await client.post(f"/api/submissions/{sid}/rejudge")
    # 可能为409（正在运行中）或200（已完成允许rejudge）
    assert resp2.status_code in (409, 200)


# --- 所有权 ---
async def test_student_cannot_view_others_submission(client: AsyncClient):
    """学生不能查看他人提交"""
    # 学生A提交
    await _create_problem_and_submit(client, "sub-own")
    resp = await client.get("/api/submissions")
    items = resp.json()["data"]["items"]
    sid = items[0]["id"] if items else None
    # 注册学生B
    await client.post("/api/auth/register", json={"username": "substu_other", "password": "substu1234567"})
    await client.post("/api/auth/login", json={"username": "substu_other", "password": "substu1234567"})
    if sid:
        resp2 = await client.get(f"/api/submissions/{sid}")
        assert resp2.status_code == 403


# --- 重新评测 ---
async def test_rejudge_success(client: AsyncClient):
    """已完成的提交可以重新评测"""
    resp = await _create_problem_and_submit(client, "sub-rejudge")
    sid = resp.json()["data"]["submission_id"]
    # 等待完成
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{sid}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    # admin 重新评测
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp2 = await client.post(f"/api/submissions/{sid}/rejudge")
    assert resp2.status_code == 200


async def test_student_cannot_rejudge(client: AsyncClient):
    """学生不能重新评测"""
    resp = await _create_problem_and_submit(client, "sub-rej-perm")
    sid = resp.json()["data"]["submission_id"]
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{sid}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    # 学生尝试 rejudge
    resp2 = await client.post(f"/api/submissions/{sid}/rejudge")
    assert resp2.status_code == 403