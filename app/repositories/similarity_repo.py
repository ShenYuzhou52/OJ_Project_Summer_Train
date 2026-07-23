"""
相似度报告数据访问层
负责 similarity_reports 表的 CRUD 操作
"""
from app.repositories.database import get_db


async def save_similarity_report(report: dict):
    """保存相似度报告到数据库"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO similarity_reports (id, problem_id, submission_a, submission_b, similarity, method, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (report["id"], report["problem_id"], report["submission_a"],
             report["submission_b"], report["similarity"], report["method"], report["created_at"])
        )
        await db.commit()
    finally:
        await db.close()


async def get_similarity_reports(problem_id: str) -> list[dict]:
    """获取某题目的所有相似度报告"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM similarity_reports WHERE problem_id = ? ORDER BY created_at DESC",
            (problem_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()