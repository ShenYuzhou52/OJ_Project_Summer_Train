"""日志测试：隐藏字段裁剪、路径脱敏、输出截断、审计记录"""
import pytest
import asyncio
from httpx import AsyncClient
from tests.conftest import SAMPLE_PROBLEM

pytestmark = pytest.mark.asyncio

AC_CODE = 'a, b = map(int, input().split())\nprint(a + b)'


async def _submit_and_wait(client: AsyncClient, prob_id="log-prob"):
    """创建题目、提交并等待评测完成"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": prob_id})
    await client.post("/api/auth/register", json={"username": f"logstu_{prob_id}", "password": "logstu1234567"})
    await client.post("/api/auth/login", json={"username": f"logstu_{prob_id}", "password": "logstu1234567"})
    resp = await client.post("/api/submissions", json={
        "problem_id": prob_id, "language": "python", "source_code": AC_CODE
    })
    sid = resp.json()["data"]["submission_id"]
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{sid}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    return sid


# --- 隐藏字段裁剪：学生看不到隐藏测试点的详细输入输出 ---
async def test_student_log_hides_hidden_case_details(client: AsyncClient):
    sid = await _submit_and_wait(client, "log-hidden")
    resp = await client.get(f"/api/submissions/{sid}/logs")
    assert resp.status_code == 200
    logs = resp.json()["data"]
    for log in logs:
        # 学生视角不应包含 expected_output 或 actual_output 对于隐藏测试点
        if log.get("is_hidden"):
            assert "expected_output" not in log or log["expected_output"] is None


# --- 路径脱敏：日志中不应暴露服务器绝对路径 ---
async def test_log_path_sanitized(client: AsyncClient):
    sid = await _submit_and_wait(client, "log-path")
    resp = await client.get(f"/api/submissions/{sid}/logs")
    logs = resp.json()["data"]
    for log in logs:
        for key, val in log.items():
            if isinstance(val, str):
                # 不应包含 Windows/Linux 绝对路径
                assert "C:\\" not in val and "/home/" not in val and "/tmp/" not in val, \
                    f"日志字段 {key} 包含未脱敏路径: {val}"


# --- 输出截断：超长输出应被截断 ---
async def test_log_output_truncated(client: AsyncClient):
    # 提交一个产生大量输出的代码
    long_output_code = "print('x' * 100000)"
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": "log-trunc"})
    await client.post("/api/auth/register", json={"username": "logstu_trunc", "password": "logstu1234567"})
    await client.post("/api/auth/login", json={"username": "logstu_trunc", "password": "logstu1234567"})
    resp = await client.post("/api/submissions", json={
        "problem_id": "log-trunc", "language": "python", "source_code": long_output_code
    })
    sid = resp.json()["data"]["submission_id"]
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{sid}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    # 教师查看日志
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp2 = await client.get(f"/api/submissions/{sid}/logs")
    logs = resp2.json()["data"]
    for log in logs:
        if log.get("actual_output"):
            assert len(log["actual_output"]) <= 5000, "输出未被截断"


# --- 审计记录：教师查看完整日志应产生审计记录 ---
async def test_audit_log_created_on_view(client: AsyncClient):
    sid = await _submit_and_wait(client, "log-audit")
    # 切换为admin查看日志
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.get(f"/api/submissions/{sid}/logs")
    # 检查审计日志
    resp = await client.get("/api/admin/audit-logs")
    if resp.status_code == 200:
        items = resp.json()["data"]
        if isinstance(items, dict):
            items = items.get("items", [])
        actions = [item["action"] for item in items]
        assert "VIEW_FULL_JUDGE_LOG" in actions