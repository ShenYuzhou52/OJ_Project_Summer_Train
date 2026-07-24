"""
评测服务主逻辑
负责评测流程编排：多测试点评测、日志写入、结果汇总
所有比较方式统一调用 comparator 模块
"""
import asyncio
import sys

from app.judge.runner import run_single_case
from app.judge.comparator import compare_output, compare_strict, run_spj
from app.utils.sanitize import truncate_text, sanitize_error_message
from app.repositories import submission_repo, judge_log_repo, problem_repo
from app.repositories.audit_log_repo import create_audit_log
from app.utils.time_utils import now_utc


def determine_final_result(cases: list[dict]) -> str:
    """根据各测试点结果确定最终评测结果"""
    has_se = any(c["result"] == "SE" for c in cases)
    has_tle = any(c["result"] == "TLE" for c in cases)
    has_re = any(c["result"] == "RE" for c in cases)
    all_ac = all(c["result"] == "AC" for c in cases)

    if all_ac:
        return "AC"
    if has_se:
        return "SE"
    if has_tle:
        return "TLE"
    if has_re:
        return "RE"
    return "WA"


async def judge_submission(submission_id: str):
    """对单次提交进行完整评测"""
    await submission_repo.update_submission_status(
        submission_id, "running", started_at=now_utc()
    )

    # 审计日志：评测开始
    await create_audit_log("system", "JUDGE_STARTED", "submission", submission_id)

    try:
        submission = await submission_repo.get_submission_by_id(submission_id)
        problem = await problem_repo.get_problem_by_id(submission["problem_id"])

        if problem is None:
            raise Exception(f"Problem {submission['problem_id']} not found")

        test_cases = problem["test_cases"]
        source_code = submission["source_code"]
        time_limit = problem["time_limit"]
        judge_mode = problem.get("judge_mode", "standard")
        spj_code = problem.get("spj_code")

        case_results = []
        total_score = 0
        total_time = 0.0
        stop_early = False

        for tc in test_cases:
            if stop_early:
                break
            raw_result = await run_single_case(source_code, tc["input"], time_limit)

            # 超时和系统错误可以直接判定
            if raw_result["result"] in ("TLE", "SE"):
                case_result = raw_result["result"]
                exit_code = raw_result["exit_code"]
                stdout = raw_result["stdout"]
                stderr = raw_result["stderr"]
                time_used = raw_result["time_used"]
                score = 0
                message = "Time Limit Exceeded" if case_result == "TLE" else "System Error"
                stop_early = True

                # 审计日志：发生超时 / 发生评测系统错误
                if case_result == "TLE":
                    await create_audit_log(
                        "system", "JUDGE_TLE", "submission", submission_id,
                        detail=f"case_id={tc['case_id']}, time_used={time_used:.3f}s"
                    )
                else:
                    await create_audit_log(
                        "system", "JUDGE_SYSTEM_ERROR", "submission", submission_id,
                        detail=f"case_id={tc['case_id']}, stderr={truncate_text(stderr, 200)}"
                    )
            elif raw_result["exit_code"] != 0:
                case_result = "RE"
                exit_code = raw_result["exit_code"]
                stdout = raw_result["stdout"]
                stderr = raw_result["stderr"]
                time_used = raw_result["time_used"]
                score = 0
                message = "Runtime Error"
                stop_early = True

                # 审计日志：发生运行错误
                await create_audit_log(
                    "system", "JUDGE_RUNTIME_ERROR", "submission", submission_id,
                    detail=f"case_id={tc['case_id']}, exit_code={exit_code}"
                )
            else:
                exit_code = raw_result["exit_code"]
                stdout = raw_result["stdout"]
                stderr = raw_result["stderr"]
                time_used = raw_result["time_used"]

                # 根据 judge_mode 调用对应的比较方式
                if judge_mode == "spj" and spj_code:
                    spj_result = await run_spj(spj_code, tc["input"], tc["output"], stdout)
                    if spj_result.get("result") == "SE":
                        case_result = "SE"
                        score = 0
                        message = spj_result.get("message", "SPJ Error")
                        stop_early = True
                        # 审计日志：SPJ 系统错误
                        await create_audit_log(
                            "system", "JUDGE_SYSTEM_ERROR", "submission", submission_id,
                            detail=f"case_id={tc['case_id']}, SPJ error: {message}"
                        )
                    elif spj_result.get("accepted"):
                        case_result = "AC"
                        score = tc["score"]
                        message = spj_result.get("message", "Accepted")
                    else:
                        case_result = "WA"
                        score = 0
                        message = spj_result.get("message", "Wrong Answer")
                elif judge_mode == "strict":
                    if compare_strict(stdout, tc["output"]):
                        case_result = "AC"
                        score = tc["score"]
                        message = "Accepted"
                    else:
                        case_result = "WA"
                        score = 0
                        message = "Wrong Answer"
                else:
                    # standard mode: 规范化比较
                    if compare_output(stdout, tc["output"]):
                        case_result = "AC"
                        score = tc["score"]
                        message = "Accepted"
                    else:
                        case_result = "WA"
                        score = 0
                        message = "Wrong Answer"

            total_score += score
            total_time += time_used

            await judge_log_repo.create_judge_log(
                submission_id=submission_id,
                case_id=tc["case_id"],
                result=case_result,
                score=score,
                time_used=time_used,
                exit_code=exit_code,
                input_data=truncate_text(tc["input"]),
                stdout=truncate_text(stdout),
                stderr=truncate_text(stderr),
                expected_output=truncate_text(tc["output"]),
                message=message,
                is_hidden=tc["is_hidden"]
            )

            # 审计日志：每个测试点执行结束
            await create_audit_log(
                "system", "JUDGE_CASE_FINISHED", "submission", submission_id,
                detail=f"case_id={tc['case_id']}, result={case_result}, score={score}"
            )

            case_results.append({"case_id": tc["case_id"], "result": case_result, "score": score})

        final_result = determine_final_result(case_results)

        # SE 时 status 应为 "failed"，其他结果为 "finished"
        status = "failed" if final_result == "SE" else "finished"
        await submission_repo.update_submission_status(
            submission_id, status, result=final_result,
            score=total_score, total_time=total_time,
            finished_at=now_utc()
        )

        # 审计日志：整次评测结束
        await create_audit_log(
            "system", "JUDGE_FINISHED", "submission", submission_id,
            detail=f"result={final_result}, score={total_score}, total_time={total_time:.3f}s"
        )

    except Exception as e:
        import traceback
        print(f"[JUDGE ERROR] submission {submission_id}: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)

        await submission_repo.update_submission_status(
            submission_id, "failed", result="SE",
            finished_at=now_utc()
        )

        # 审计日志：发生评测系统错误（异常级别）
        await create_audit_log(
            "system", "JUDGE_SYSTEM_ERROR", "submission", submission_id,
            detail=f"exception: {str(e)[:200]}"
        )