"""题目管理测试：创建、查询、修改、删除、重复编号、字段校验、隐藏测试点、权限"""
import pytest
from httpx import AsyncClient
from tests.conftest import SAMPLE_PROBLEM

pytestmark = pytest.mark.asyncio


# --- 创建题目 ---
async def test_create_problem_success(admin_client: AsyncClient):
    resp = await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    assert resp.status_code == 201
    assert resp.json()["data"]["id"] == "test-prob-01"


# --- 查询题目 ---
async def test_get_problem(admin_client: AsyncClient):
    await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    resp = await admin_client.get("/api/problems/test-prob-01")
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "A+B Problem"


async def test_list_problems(admin_client: AsyncClient):
    await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    resp = await admin_client.get("/api/problems")
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] >= 1


# --- 修改题目 ---
async def test_update_problem(admin_client: AsyncClient):
    await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    resp = await admin_client.put("/api/problems/test-prob-01", json={"title": "Updated Title"})
    assert resp.status_code == 200
    resp2 = await admin_client.get("/api/problems/test-prob-01")
    assert resp2.json()["data"]["title"] == "Updated Title"


# --- 删除题目 ---
async def test_delete_problem(admin_client: AsyncClient):
    await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    resp = await admin_client.delete("/api/problems/test-prob-01")
    assert resp.status_code == 200
    resp2 = await admin_client.get("/api/problems/test-prob-01")
    assert resp2.status_code == 404


# --- 重复编号 ---
async def test_duplicate_problem_id(admin_client: AsyncClient):
    await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    resp = await admin_client.post("/api/problems", json=SAMPLE_PROBLEM)
    assert resp.status_code == 409


# --- 字段校验 ---
async def test_create_problem_missing_title(admin_client: AsyncClient):
    bad = {**SAMPLE_PROBLEM, "title": ""}
    resp = await admin_client.post("/api/problems", json=bad)
    assert resp.status_code == 422


async def test_create_problem_invalid_time_limit(admin_client: AsyncClient):
    bad = {**SAMPLE_PROBLEM, "id": "bad-tl", "time_limit": -1}
    resp = await admin_client.post("/api/problems", json=bad)
    assert resp.status_code == 422


async def test_create_problem_score_not_100(admin_client: AsyncClient):
    bad = {**SAMPLE_PROBLEM, "id": "bad-score", "test_cases": [
        {"case_id": "tc1", "input": "1", "output": "1", "score": 30, "is_hidden": False},
        {"case_id": "tc2", "input": "2", "output": "2", "score": 30, "is_hidden": False},
    ]}
    resp = await admin_client.post("/api/problems", json=bad)
    assert resp.status_code == 422


async def test_create_problem_duplicate_case_ids(admin_client: AsyncClient):
    bad = {**SAMPLE_PROBLEM, "id": "bad-caseid", "test_cases": [
        {"case_id": "tc1", "input": "1", "output": "1", "score": 50, "is_hidden": False},
        {"case_id": "tc1", "input": "2", "output": "2", "score": 50, "is_hidden": False},
    ]}
    resp = await admin_client.post("/api/problems", json=bad)
    assert resp.status_code == 422


# --- 隐藏测试点 ---
async def test_student_cannot_see_hidden_test_cases(client: AsyncClient):
    # admin 创建题目
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json=SAMPLE_PROBLEM)
    await client.post("/api/auth/logout")
    # 学生查看
    await client.post("/api/auth/register", json={"username": "stu_hidden", "password": "stu_hidden123"})
    await client.post("/api/auth/login", json={"username": "stu_hidden", "password": "stu_hidden123"})
    resp = await client.get("/api/problems/test-prob-01")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # 学生不应该看到 test_cases 或 test_cases 中的隐藏部分
    if data.get("test_cases"):
        for tc in data["test_cases"]:
            assert tc.get("is_hidden") is not True or "input" not in tc


# --- 权限：学生不能创建/修改/删除 ---
async def test_student_cannot_create_problem(student_client: AsyncClient):
    resp = await student_client.post("/api/problems", json=SAMPLE_PROBLEM)
    assert resp.status_code == 403


async def test_student_cannot_update_problem(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json=SAMPLE_PROBLEM)
    await client.post("/api/auth/logout")
    await client.post("/api/auth/register", json={"username": "stu_upd", "password": "stu_upd12345"})
    await client.post("/api/auth/login", json={"username": "stu_upd", "password": "stu_upd12345"})
    resp = await client.put("/api/problems/test-prob-01", json={"title": "Hacked"})
    assert resp.status_code == 403


async def test_student_cannot_delete_problem(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json=SAMPLE_PROBLEM)
    await client.post("/api/auth/logout")
    await client.post("/api/auth/register", json={"username": "stu_del", "password": "stu_del12345"})
    await client.post("/api/auth/login", json={"username": "stu_del", "password": "stu_del12345"})
    resp = await client.delete("/api/problems/test-prob-01")
    assert resp.status_code == 403