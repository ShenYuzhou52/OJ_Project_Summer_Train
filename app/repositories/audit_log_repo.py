import uuid
from app.repositories.database import get_db
from app.utils.time_utils import now_utc


async def create_audit_log(operator_id: str, action: str, target_type: str = None,
                            target_id: str = None, success: bool = True, detail: str = None) -> dict:
    db = await get_db()
    try:
        log_id = str(uuid.uuid4())
        timestamp = now_utc()
        await db.execute(
            "INSERT INTO audit_logs (id, operator_id, action, target_type, target_id, success, detail, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, operator_id, action, target_type, target_id, 1 if success else 0, detail, timestamp)
        )
        await db.commit()
        return {"id": log_id, "action": action}
    finally:
        await db.close()


async def search_audit_logs(page: int = 1, page_size: int = 20,
                             operator_id: str | None = None, action: str | None = None,
                             target_id: str | None = None,
                             start_time: str | None = None, end_time: str | None = None) -> tuple[list, int]:
    db = await get_db()
    try:
        conditions = []
        params = []
        if operator_id:
            conditions.append("operator_id LIKE ?")
            params.append(f"%{operator_id}%")
        if action:
            conditions.append("action LIKE ?")
            params.append(f"%{action}%")
        if target_id:
            conditions.append("target_id LIKE ?")
            params.append(f"%{target_id}%")
        if start_time:
            conditions.append("created_at >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("created_at <= ?")
            params.append(end_time)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor = await db.execute(f"SELECT COUNT(*) FROM audit_logs {where}", params)
        total = (await cursor.fetchone())[0]
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"SELECT * FROM audit_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()
