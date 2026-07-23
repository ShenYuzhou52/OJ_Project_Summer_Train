import aiosqlite
import json
from app.repositories.database import get_db
from app.utils.time_utils import now_utc

async def create_user(username: str, password_hash: str, role: str = "student") -> dict:
    import uuid
    user_id = str(uuid.uuid4())
    timestamp = now_utc()
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO users (id, username, password_hash, role, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (user_id, username, password_hash, role, timestamp, timestamp)
        )
        await db.commit()
        return await get_user_by_id(user_id)
    finally:
        await db.close()

async def get_user_by_id(user_id: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

async def get_user_by_username(username: str) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

async def update_user(user_id: str, role: str | None = None, is_active: bool | None = None) -> dict | None:
    db = await get_db()
    try:
        updates = []
        params = []
        if role is not None:
            updates.append("role = ?")
            params.append(role)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)
        updates.append("updated_at = ?")
        params.append(now_utc())
        params.append(user_id)
        await db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        await db.commit()
        return await get_user_by_id(user_id)
    finally:
        await db.close()

async def update_password(user_id: str, new_password_hash: str) -> bool:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_password_hash, now_utc(), user_id)
        )
        await db.commit()
        return True
    finally:
        await db.close()

async def username_exists(username: str) -> bool:  #判重
    return await get_user_by_username(username) is not None


async def list_users(page: int = 1, page_size: int = 20, username: str | None = None,
                     role: str | None = None, is_active: bool | None = None) -> tuple[list, int]:
    db = await get_db()
    try:
        conditions = []
        params = []
        if username:
            conditions.append("username LIKE ?")
            params.append(f"%{username}%")
        if role:
            conditions.append("role = ?")
            params.append(role)
        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(1 if is_active else 0)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        cursor = await db.execute(f"SELECT COUNT(*) FROM users{where}", params)
        total = (await cursor.fetchone())[0]
        offset = (page - 1) * page_size
        cursor = await db.execute(f"SELECT * FROM users{where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [page_size, offset])
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()
