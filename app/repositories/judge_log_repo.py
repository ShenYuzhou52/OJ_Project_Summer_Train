import aiosqlite
import uuid
from app.repositories.database import get_db
from app.utils.time_utils import now_utc


async def create_judge_log(submission_id: str, case_id: str, result: str, score: int,
                            time_used: float, exit_code: int, input_data: str,
                            stdout: str, stderr: str, expected_output: str,
                            message: str, is_hidden: bool, memory_used: float = None) -> dict:
    db = await get_db()
    try:
        log_id = str(uuid.uuid4()) #获得独一无二的id
        timestamp = now_utc()
        await db.execute(
            "INSERT INTO judge_logs (id, submission_id, case_id, result, score, time_used, memory_used, exit_code, input_data, stdout, stderr, expected_output, message, is_hidden, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, submission_id, case_id, result, score, time_used, memory_used, exit_code,
             input_data, stdout, stderr, expected_output, message, 1 if is_hidden else 0, timestamp)
        )
        await db.commit()
        return {"id": log_id, "submission_id": submission_id, "case_id": case_id}
    finally:
        await db.close()


async def get_logs_by_submission(submission_id: str) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM judge_logs WHERE submission_id = ? ORDER BY created_at", (submission_id,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def delete_logs_by_submission(submission_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM judge_logs WHERE submission_id = ?", (submission_id,))
        await db.commit()
    finally:
        await db.close()


async def search_logs(page: int = 1, page_size: int = 20,
                       submission_id: str | None = None, problem_id: str | None = None,
                       user_id: str | None = None, result: str | None = None,
                       start_time: str | None = None, end_time: str | None = None) -> tuple[list, int]:
    db = await get_db()
    try:
        conditions = []
        params = []
        if submission_id:
            conditions.append("jl.submission_id LIKE ?")
            params.append(f"%{submission_id}%")
        if result:
            conditions.append("jl.result LIKE ?")
            params.append(f"%{result}%")
        if start_time:
            conditions.append("jl.created_at >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("jl.created_at <= ?")
            params.append(end_time)

        joins = ""
        if problem_id or user_id:
            joins += " JOIN submissions s ON jl.submission_id = s.id"
            if problem_id:
                conditions.append("s.problem_id LIKE ?")
                params.append(f"%{problem_id}%")
            if user_id:
                conditions.append("s.user_id LIKE ?")
                params.append(f"%{user_id}%")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor = await db.execute(f"SELECT COUNT(*) FROM judge_logs jl {joins} {where}", params)
        total = (await cursor.fetchone())[0]
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT jl.* FROM judge_logs jl {joins} {where} ORDER BY jl.created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()
