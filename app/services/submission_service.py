import uuid
from app.repositories import submission_repo, problem_repo
from app.judge.judge_service import judge_submission
from app.repositories.audit_log_repo import create_audit_log
from fastapi import BackgroundTasks

async def create_and_judge(user_id: str, problem_id: str, language: str, source_code: str, background_tasks: BackgroundTasks) -> dict:
    #创建提交，异步启动评测
    if not await problem_repo.problem_exists(problem_id):
        return None

    submission_id = str(uuid.uuid4())  #随机分配不重复的唯一id，全局唯一，不可预测，无需中心化分配
    submission = await submission_repo.create_submission(
        submission_id, user_id, problem_id, language, source_code
    )

    # 使用 FastAPI 的 BackgroundTasks 确保任务能够正确执行
    background_tasks.add_task(judge_submission, submission_id)

    return submission

async def rejudge(submission_id: str, operator_id: str, background_tasks: BackgroundTasks) -> dict | str:
    """重新判题，使用原子性状态检查防止并发 rejudge 竞态。"""
    submission = await submission_repo.get_submission_by_id(submission_id)
    if not submission:
        return "not found"
    if submission["status"] not in ("finished", "failed"):
        return "conflict"  # 正在 pending/running 的提交不允许 rejudge
    
    # 原子性重置：仅当状态仍为 finished/failed 时才更新
    # 如果并发请求已经抢先重置了，这里会返回 False
    reset_ok = await submission_repo.reset_submission_for_rejudge(submission_id)
    if not reset_ok:
        return "conflict"

    # 删除旧的评测日志
    from app.repositories.judge_log_repo import delete_logs_by_submission
    await delete_logs_by_submission(submission_id)

    # 记录审计日志
    await create_audit_log(operator_id, "REJUDGE_SUBMISSION", "submission", submission_id)

    # 启动后台评测任务
    background_tasks.add_task(judge_submission, submission_id)

    return {"submission_id": submission_id, "status": "pending"}