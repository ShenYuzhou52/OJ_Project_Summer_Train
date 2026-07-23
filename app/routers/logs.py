from fastapi import APIRouter, Request, Depends, Query
from app.repositories import judge_log_repo, submission_repo
from app.repositories.audit_log_repo import create_audit_log
from app.utils.deps import get_current_user, RequireRole
from app.utils.sanitize import to_student_log_view, to_teacher_log_view
from app.utils.response import ok, error_resp

router = APIRouter(tags=["logs"])

@router.get("/api/submissions/{submission_id}/logs")
async def get_submission_logs(submission_id: str, user: dict = Depends(get_current_user)):
    submission = await submission_repo.get_submission_by_id(submission_id)
    if not submission:
        return error_resp(404, "submission not found")
    if user["role"] == "student" and submission["user_id"] != user["id"]:
        return error_resp(403, "cannot view others' logs")
    logs = await judge_log_repo.get_logs_by_submission(submission_id)

    if user["role"] == "student":
        views = [to_student_log_view(log) for log in logs]
    else:
        await create_audit_log(user["id"], "VIEW_FULL_JUDGE_LOG", "submission", submission_id)
        views = [to_teacher_log_view(log) for log in logs]

    return ok(views)

@router.get("/api/logs")
async def search_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    submission_id: str = None, problem_id: str = None,
    user_id: str = None, result: str = None,
    start_time: str = None, end_time: str = None,
    user: dict = Depends(RequireRole("teacher", "admin")),
):
    logs, total = await judge_log_repo.search_logs(
        page, page_size, submission_id, problem_id, user_id, result, start_time, end_time
    )
    views = [to_teacher_log_view(log) for log in logs]
    return ok({"items": views, "total": total, "page": page, "page_size": page_size})