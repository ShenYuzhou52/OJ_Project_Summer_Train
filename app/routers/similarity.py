from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.utils.deps import RequireRole
from app.utils.response import ok, error_resp
from app.services.similarity_service import run_similarity_check, get_similarity_reports
from app.repositories.problem_repo import problem_exists

router = APIRouter(prefix="/api/problems", tags=["similarity"])

SIMILARITY_THRESHOLD = 0.9


class SimilarityCheckRequest(BaseModel):
    submission_ids: list[str] = Field(min_length=2, description="待比较的 submission_id 列表，至少2个")


@router.post("/{problem_id}/similarity-check")
async def check_similarity(
    problem_id: str,
    req: SimilarityCheckRequest,
    user: dict = Depends(RequireRole("teacher", "admin"))
):
    """对指定题目的多份提交进行两两相似度检测"""
    if not await problem_exists(problem_id):
        return error_resp(404, "problem not found")

    reports = await run_similarity_check(problem_id, req.submission_ids)

    if not reports:
        return error_resp(400, "无法获取足够的有效提交进行比较（提交不存在或不属于该题目）")

    # 标注高于阈值的报告
    for r in reports:
        r["above_threshold"] = r["similarity"] >= SIMILARITY_THRESHOLD

    return ok({
        "problem_id": problem_id,
        "threshold": SIMILARITY_THRESHOLD,
        "total_pairs": len(reports),
        "flagged_pairs": sum(1 for r in reports if r["above_threshold"]),
        "reports": reports,
    })


@router.get("/{problem_id}/similarity-reports")
async def list_similarity_reports(
    problem_id: str,
    user: dict = Depends(RequireRole("teacher", "admin"))
):
    """获取某题目的所有历史相似度报告"""
    if not await problem_exists(problem_id):
        return error_resp(404, "problem not found")

    reports = await get_similarity_reports(problem_id)

    # 标注高于阈值的
    for r in reports:
        r["above_threshold"] = r["similarity"] >= SIMILARITY_THRESHOLD

    return ok({
        "problem_id": problem_id,
        "threshold": SIMILARITY_THRESHOLD,
        "total_pairs": len(reports),
        "flagged_pairs": sum(1 for r in reports if r["above_threshold"]),
        "reports": reports,
    })