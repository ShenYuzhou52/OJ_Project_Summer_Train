import aiosqlite
from app.repositories.database import get_db
from app.utils.time_utils import now_utc


async def create_submission(submission_id: str, user_id: str, problem_id: str, language: str, source_code: str) -> dict:
    db = await get_db()
    try:
        timestamp = now_utc()
        await db.execute(
            "INSERT INTO submissions (id, user_id, problem_id, language, source_code, status, result, score, total_time, created_at, started_at, finished_at) VALUES (?, ?, ?, ?, ?, 'pending', NULL, 0, NULL, ?, NULL, NULL)",
            (submission_id, user_id, problem_id, language, source_code, timestamp)
        )
        await db.commit()
        return await get_submission_by_id(submission_id)
    finally:
        await db.close()


async def get_submission_by_id(submission_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def update_submission_status(submission_id: str, status: str, result: str | None = None,
                                    score: int | None = None, total_time: float | None = None,
                                    started_at: str | None = None, finished_at: str | None = None):
    db = await get_db()
    try:
        sets = ["status = ?"]
        params = [status]
        if result is not None:
            sets.append("result = ?")
            params.append(result)
        if score is not None:
            sets.append("score = ?")
            params.append(score)
        if total_time is not None:
            sets.append("total_time = ?")
            params.append(total_time)
        if started_at is not None:
            sets.append("started_at = ?")
            params.append(started_at)
        if finished_at is not None:
            sets.append("finished_at = ?")
            params.append(finished_at)
        params.append(submission_id)
        await db.execute(f"UPDATE submissions SET {', '.join(sets)} WHERE id = ?", params)
        await db.commit()
    finally:
        await db.close()


async def reset_submission_for_rejudge(submission_id: str) -> bool:
    """原子性地重置提交状态为pending，仅当当前状态为finished或failed时生效。
    返回True表示成功重置，False表示状态不符（可能被并发请求抢占）。"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE submissions SET status='pending', result=NULL, score=0, total_time=NULL, started_at=NULL, finished_at=NULL WHERE id=? AND status IN ('finished', 'failed')",
            (submission_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def list_submissions(page: int = 1, page_size: int = 20,
                            user_id: str | None = None, problem_id: str | None = None,
                            status: str | None = None, result: str | None = None,
                            start_time: str | None = None, end_time: str | None = None,
                            submission_id: str | None = None) -> tuple[list, int]:
    db = await get_db()
    try:
        conditions = []
        params = []
        if submission_id:
            conditions.append("id LIKE ?")
            params.append(f"%{submission_id}%")
        if user_id:
            conditions.append("user_id LIKE ?")
            params.append(f"%{user_id}%")
        if problem_id:
            conditions.append("problem_id LIKE ?")
            params.append(f"%{problem_id}%")
        if status:
            conditions.append("status = ?")
            params.append(status)
        if result:
            conditions.append("result LIKE ?")
            params.append(f"%{result}%")
        if start_time:
            conditions.append("created_at >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("created_at <= ?")
            params.append(end_time)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor = await db.execute(f"SELECT COUNT(*) FROM submissions {where}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM submissions {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()