import uuid
import aiosqlite
from app.repositories.database import get_db


async def create_test_cases(problem_id: str, test_cases: list[dict]) -> list[dict]:
    """批量创建测试点"""
    db = await get_db()
    try:
        rows = []
        for tc in test_cases:
            tc_id = tc.get("id") or str(uuid.uuid4())
            await db.execute(
                "INSERT INTO test_cases (id, problem_id, case_id, input, expected_output, score, is_hidden) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tc_id, problem_id, tc["case_id"], tc["input"], tc["output"], tc["score"], 1 if tc.get("is_hidden") else 0)
            )
            rows.append({"id": tc_id, "problem_id": problem_id, "case_id": tc["case_id"],
                         "input": tc["input"], "output": tc["output"],
                         "score": tc["score"], "is_hidden": tc.get("is_hidden", False)})
        await db.commit()
        return rows
    finally:
        await db.close()


async def get_test_cases_by_problem(problem_id: str) -> list[dict]:
    """获取某题目的所有测试点"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM test_cases WHERE problem_id = ? ORDER BY case_id",
            (problem_id,)
        )
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            row = dict(r)
            result.append({
                "case_id": row["case_id"],
                "input": row["input"],
                "output": row["expected_output"],
                "score": row["score"],
                "is_hidden": bool(row["is_hidden"]),
            })
        return result
    finally:
        await db.close()


async def delete_test_cases_by_problem(problem_id: str):
    """删除某题目的所有测试点"""
    db = await get_db()
    try:
        await db.execute("DELETE FROM test_cases WHERE problem_id = ?", (problem_id,))
        await db.commit()
    finally:
        await db.close()


async def replace_test_cases(problem_id: str, test_cases: list[dict]) -> list[dict]:
    """替换某题目的所有测试点（先删后增）"""
    await delete_test_cases_by_problem(problem_id)
    return await create_test_cases(problem_id, test_cases)