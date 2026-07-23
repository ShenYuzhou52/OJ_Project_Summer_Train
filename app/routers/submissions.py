from fastapi import APIRouter, Request, Depends, Query, BackgroundTasks
from app.models.submission import SubmissionCreateRequest
from app.services.submission_service import create_and_judge, rejudge
from app.repositories import submission_repo
from app.utils.deps import get_current_user, RequireRole
from app.utils.response import ok, error_resp, accepted_resp

router = APIRouter(prefix = "/api/submissions", tags = ["submissions"])

@router.post("")
async def create_submission(req: SubmissionCreateRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    if req.language != 'python':
        return error_resp(400, "only python is supported!")
    if len(req.source_code.encode("utf-8")) > 64*1024:
        return error_resp(400, "source code exceeds 64 KiB")
    
    submission = await create_and_judge(user["id"], req.problem_id, req.language, req.source_code, background_tasks)
    if submission is None:
        return error_resp(404, "problem not found!")
    return accepted_resp(
        {"submission_id": submission["id"], "status": submission["status"]},
        message = "submission accepted"
    )

@router.get("")
async def list_submissions(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    submission_id: str = None, problem_id: str = None, user_id: str = None,
    status: str = None, result: str = None,
    start_time: str = None, end_time: str = None,
    user: dict = Depends(get_current_user),
):
    if user["role"] == "student":
        user_id = user["id"]
    
    submissions, total = await submission_repo.list_submissions(
        page, page_size, user_id, problem_id, status, result, start_time, end_time, submission_id
    )
    items = [{
        "id": s["id"], "user_id": s["user_id"], "problem_id": s["problem_id"],
        "language": s["language"], "status": s["status"], "result": s["result"],
        "score": s["score"], "total_time": s["total_time"], "created_at": s["created_at"],
    } for s in submissions]
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})


@router.get("/{submission_id}")
async def get_submission(submission_id: str, user: dict = Depends(get_current_user)):
    submission = await submission_repo.get_submission_by_id(submission_id)
    if not submission:
        return error_resp(404, "submission not found")
    if user["role"] == "student" and submission["user_id"] != user["id"]:
        return error_resp(403, "cannot view others' submission")
    # 构建返回数据，包含 started_at 和 finished_at
    data = {
        "id": submission["id"], "user_id": submission["user_id"],
        "problem_id": submission["problem_id"], "language": submission["language"],
        "status": submission["status"], "result": submission["result"],
        "score": submission["score"], "total_time": submission["total_time"],
        "created_at": submission["created_at"],
        "started_at": submission.get("started_at"),
        "finished_at": submission.get("finished_at"),
    }
    # 自己的提交或教师/管理员可以看到源代码
    if user["role"] in ("teacher", "admin") or submission["user_id"] == user["id"]:
        data["source_code"] = submission["source_code"]
    return ok(data)

@router.post("/{submission_id}/rejudge")
async def rejudge_submission(submission_id: str, background_tasks: BackgroundTasks, user: dict = Depends(RequireRole("teacher","admin"))):
    result = await rejudge(submission_id, user["id"], background_tasks)
    if result == "not found":
        return error_resp(404, "submission not found")
    if result == "conflict":
        return error_resp(409, "submission cannot be rejudged")
    return ok(result, message="rejudge started")