import aiosqlite
import json
from app.repositories.database import get_db
from app.repositories.test_case_repo import (
    create_test_cases, get_test_cases_by_problem,
    replace_test_cases, delete_test_cases_by_problem,
)
from app.utils.time_utils import now_utc


async def create_problem(problem_data: dict) -> dict:
    db = await get_db()
    try:
        timestamp = now_utc()
        # 将 test_cases 序列化存入 problems 表（保持向后兼容），同时写入独立表
        test_cases_list = problem_data["test_cases"]
        # 如果 test_cases 元素是 Pydantic model，转为 dict
        if test_cases_list and hasattr(test_cases_list[0], "model_dump"):
            test_cases_list = [tc.model_dump() for tc in test_cases_list]
        await db.execute(
            "INSERT INTO problems (id, title, description, input_description, output_description, samples, constraints, time_limit, memory_limit, difficulty, tags, test_cases, judge_mode, spj_code, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (problem_data["id"], problem_data["title"], problem_data["description"],
             problem_data["input_description"], problem_data["output_description"],
             json.dumps(problem_data["samples"], ensure_ascii=False),
             problem_data.get("constraints", ""),
             problem_data["time_limit"], problem_data["memory_limit"],
             problem_data["difficulty"], json.dumps(problem_data.get("tags", []), ensure_ascii=False),
             json.dumps(test_cases_list, ensure_ascii=False),
             problem_data.get("judge_mode", "standard"),
             problem_data.get("spj_code"),
             timestamp, timestamp)
        )
        await db.commit()
        # 写入独立 test_cases 表
        await create_test_cases(problem_data["id"], test_cases_list)
        return await get_problem_by_id(problem_data["id"])
    finally:
        await db.close()


async def get_problem_by_id(problem_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM problems WHERE id = ?", (problem_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        result["samples"] = json.loads(result["samples"])
        result["tags"] = json.loads(result["tags"])
        # 保存原始 JSON 字段值用于回退
        raw_test_cases_json = result.get("test_cases", "[]")
        # 从独立 test_cases 表读取测试点
        result["test_cases"] = await get_test_cases_by_problem(problem_id)
        # 如果独立表为空，回退到 JSON 字段（兼容迁移前数据）
        if not result["test_cases"]:
            try:
                result["test_cases"] = json.loads(raw_test_cases_json) if raw_test_cases_json else []
            except Exception:
                result["test_cases"] = []
        # Ensure judge_mode has a default for old data
        if not result.get("judge_mode"):
            result["judge_mode"] = "standard"
        return result
    finally:
        await db.close()


async def list_problems(page: int = 1, page_size: int = 20, search: str = None,
                        difficulty: str = None, tag: str = None) -> tuple[list, int]:
    """获取题目列表（支持搜索、按难度筛选、按标签筛选）"""
    db = await get_db()
    try:
        conditions = []
        params = []

        if search:
            search_pattern = f"%{search}%"
            conditions.append("""(
                id LIKE ? OR 
                title LIKE ? OR 
                description LIKE ? OR 
                input_description LIKE ? OR 
                output_description LIKE ? OR 
                constraints LIKE ? OR 
                difficulty LIKE ? OR 
                tags LIKE ?
            )""")
            params.extend([search_pattern] * 8)

        if difficulty:
            conditions.append("difficulty = ?")
            params.append(difficulty)

        if tag:
            # tags 存储为 JSON 数组字符串，用 LIKE 匹配
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM problems {where_clause}"
        cursor = await db.execute(count_sql, params)
        total = (await cursor.fetchone())[0]

        # 获取分页数据
        offset = (page - 1) * page_size
        list_sql = f"SELECT * FROM problems {where_clause} ORDER BY id LIMIT ? OFFSET ?"
        cursor = await db.execute(list_sql, params + [page_size, offset])
        rows = await cursor.fetchall()

        problems = []
        for r in rows:
            p = dict(r)
            p["tags"] = json.loads(p["tags"])
            if not p.get("judge_mode"):
                p["judge_mode"] = "standard"
            problems.append(p)
        return problems, total
    finally:
        await db.close()


async def update_problem(problem_id: str, update_data: dict) -> dict | None:
    db = await get_db()
    try:
        sets = []
        params = []
        test_cases_to_sync = None
        for key, value in update_data.items():
            if value is not None:
                if key == "test_cases":
                    # 如果元素是 Pydantic model，转为 dict
                    if value and hasattr(value[0], "model_dump"):
                        value = [tc.model_dump() for tc in value]
                    test_cases_to_sync = value
                    sets.append(f"{key} = ?")
                    params.append(json.dumps(value, ensure_ascii=False))
                elif key in ("samples", "tags"):
                    sets.append(f"{key} = ?")
                    params.append(json.dumps(value, ensure_ascii=False))
                else:
                    sets.append(f"{key} = ?")
                    params.append(value)
        sets.append("updated_at = ?")
        params.append(now_utc())
        params.append(problem_id)
        await db.execute(f"UPDATE problems SET {', '.join(sets)} WHERE id = ?", params)
        await db.commit()
        # 同步更新独立 test_cases 表
        if test_cases_to_sync is not None:
            await replace_test_cases(problem_id, test_cases_to_sync)
        return await get_problem_by_id(problem_id)
    finally:
        await db.close()


async def delete_problem(problem_id: str) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM problems WHERE id = ?", (problem_id,))
        await db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            # 同步删除独立 test_cases 表中的数据
            await delete_test_cases_by_problem(problem_id)
        return deleted
    finally:
        await db.close()


async def problem_exists(problem_id: str) -> bool:
    return await get_problem_by_id(problem_id) is not None


async def update_spj_code(problem_id: str, spj_code: str | None) -> dict | None:
    """更新题目的 SPJ 代码"""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE problems SET spj_code = ?, updated_at = ? WHERE id = ?",
            (spj_code, now_utc(), problem_id)
        )
        await db.commit()
        return await get_problem_by_id(problem_id)
    finally:
        await db.close()