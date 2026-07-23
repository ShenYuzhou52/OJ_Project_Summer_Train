"""自动评测测试：AC、WA、RE、TLE、SE、多测试点、输出规范化、临时文件清理"""
import pytest
import asyncio
import os
import glob
from httpx import AsyncClient
from tests.conftest import SAMPLE_PROBLEM

pytestmark = pytest.mark.asyncio

AC_CODE = 'a, b = map(int, input().split())\nprint(a + b)'
WA_CODE = 'a, b = map(int, input().split())\nprint(a - b)'
RE_CODE = 'raise RuntimeError("crash")'
TLE_CODE = 'import time\ntime.sleep(10)'


async def _setup_problem_and_submit(client: AsyncClient, code: str, problem_id: str = "judge-prob"):
    """辅助：admin创建题目，学生提交代码"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    prob = {**SAMPLE_PROBLEM, "id": problem_id, "time_limit": 3.0}
    await client.post("/api/problems", json=prob)
    # 注册学生并提交
    await client.post("/api/auth/register", json={"username": f"judgestu_{problem_id}", "password": "judgestu12345"})
    await client.post("/api/auth/login", json={"username": f"judgestu_{problem_id}", "password": "judgestu12345"})
    resp = await client.post("/api/submissions", json={
        "problem_id": problem_id, "language": "python", "source_code": code
    })
    assert resp.status_code == 202
    submission_id = resp.json()["data"]["submission_id"]
    # 等待评测完成
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{submission_id}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            return r.json()["data"]
    return (await client.get(f"/api/submissions/{submission_id}")).json()["data"]


# --- AC ---
async def test_judge_ac(client: AsyncClient):
    result = await _setup_problem_and_submit(client, AC_CODE, "judge-ac")
    assert result["result"] == "AC"
    assert result["score"] == 100


# --- WA ---
async def test_judge_wa(client: AsyncClient):
    result = await _setup_problem_and_submit(client, WA_CODE, "judge-wa")
    assert result["result"] == "WA"
    assert result["score"] == 0


# --- RE ---
async def test_judge_re(client: AsyncClient):
    result = await _setup_problem_and_submit(client, RE_CODE, "judge-re")
    assert result["result"] == "RE"


# --- TLE ---
async def test_judge_tle(client: AsyncClient):
    # 使用短时间限制
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    prob = {**SAMPLE_PROBLEM, "id": "judge-tle", "time_limit": 1.0}
    await client.post("/api/problems", json=prob)
    await client.post("/api/auth/register", json={"username": "judgestu_tle", "password": "judgestu12345"})
    await client.post("/api/auth/login", json={"username": "judgestu_tle", "password": "judgestu12345"})
    resp = await client.post("/api/submissions", json={
        "problem_id": "judge-tle", "language": "python", "source_code": TLE_CODE
    })
    submission_id = resp.json()["data"]["submission_id"]
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{submission_id}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    data = (await client.get(f"/api/submissions/{submission_id}")).json()["data"]
    assert data["result"] == "TLE"


# --- SE ---
async def test_judge_se(client: AsyncClient):
    """评测器异常（如题目不存在导致评测失败）应返回SE"""
    # 注册学生
    await client.post("/api/auth/register", json={"username": "judgestu_se", "password": "judgestu12345"})
    await client.post("/api/auth/login", json={"username": "judgestu_se", "password": "judgestu12345"})
    # 提交到一个不存在的题目，会触发 judge_service 中的异常，返回 SE
    resp = await client.post("/api/submissions", json={
        "problem_id": "nonexistent-problem-id", "language": "python", "source_code": AC_CODE
    })
    # 题目不存在应该在提交时就返回 404，但如果提交成功了，评测时会触发 SE
    if resp.status_code == 202:
        submission_id = resp.json()["data"]["submission_id"]
        for _ in range(30):
            await asyncio.sleep(0.5)
            r = await client.get(f"/api/submissions/{submission_id}")
            if r.json()["data"]["status"] in ("finished", "failed"):
                break
        data = (await client.get(f"/api/submissions/{submission_id}")).json()["data"]
        assert data["status"] == "failed"
        assert data["result"] == "SE"


# --- 多测试点 ---
async def test_multiple_test_cases_partial_score(client: AsyncClient):
    """第一个测试点AC，第二个WA（因为隐藏测试点输入不同）"""
    # 构造一个只能通过第一个测试点的代码
    code = 'print(3)'  # 只能通过 tc1 (output="3\n")
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    prob = {**SAMPLE_PROBLEM, "id": "judge-multi"}
    await client.post("/api/problems", json=prob)
    await client.post("/api/auth/register", json={"username": "judgestu_multi", "password": "judgestu12345"})
    await client.post("/api/auth/login", json={"username": "judgestu_multi", "password": "judgestu12345"})
    resp = await client.post("/api/submissions", json={
        "problem_id": "judge-multi", "language": "python", "source_code": code
    })
    submission_id = resp.json()["data"]["submission_id"]
    for _ in range(30):
        await asyncio.sleep(0.5)
        r = await client.get(f"/api/submissions/{submission_id}")
        if r.json()["data"]["status"] in ("finished", "failed"):
            break
    data = (await client.get(f"/api/submissions/{submission_id}")).json()["data"]
    # 第一个 tc 输出 "3\n"，对了（50分），第二个 tc 期望 "7\n" 但输出 "3\n"，错了
    assert data["result"] == "WA"
    assert data["score"] == 50


# --- 输出规范化 ---
async def test_output_normalization(client: AsyncClient):
    """末尾多余空格/换行应被规范化后仍然AC"""
    code = 'a, b = map(int, input().split())\nprint(a + b, end="   \\n\\n")'  # 尾部多余空格和换行
    result = await _setup_problem_and_submit(client, code, "judge-norm")
    # standard 模式下会规范化比较
    assert result["result"] == "AC"


# --- 临时文件清理 ---
async def test_temp_files_cleaned(client: AsyncClient):
    """评测完成后临时文件应被清理"""
    import app.config as cfg
    temp_dir = cfg.TEMP_DIR
    # 记录评测前临时文件数
    before = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
    await _setup_problem_and_submit(client, AC_CODE, "judge-clean")
    await asyncio.sleep(1)
    after = set(os.listdir(temp_dir)) if os.path.exists(temp_dir) else set()
    # 评测完成后不应该有新增的临时文件残留
    new_files = after - before
    assert len(new_files) == 0, f"临时文件未清理: {new_files}"