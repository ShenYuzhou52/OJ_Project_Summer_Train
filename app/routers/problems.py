from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from typing import Optional
from app.models.problem import ProblemCreateRequest, ProblemUpdateRequest
from app.repositories import problem_repo
from app.utils.deps import get_current_user, RequireRole
from app.utils.response import ok, error_resp, created_resp

router = APIRouter(prefix = "/api/problems", tags = ["problems"]) # 统一加路径前缀

@router.get("") #告诉FastAPI当收到某个HTTP方法的请求时应该调用这个函数
async def list_problems(
    page: int = 1, page_size: int = 20,
    search: str = None, difficulty: str = None, tag: str = None,
    request: Request = None
):
    """获取题目列表（支持搜索、按难度和标签筛选）"""
    # 需要登录才能查看题目列表
    user_id = request.session.get("user_id") if request else None
    if not user_id:
        return error_resp(401, "not logged in")
    from app.repositories.user_repo import get_user_by_id
    user = await get_user_by_id(user_id)
    if not user:
        return error_resp(401, "user not found")
    if not user["is_active"]:
        return error_resp(403, "user is disabled")

    problems, total = await problem_repo.list_problems(page, page_size, search=search, difficulty=difficulty, tag=tag)
    items = []
    for p in problems:
        items.append({
             "id": p["id"], "title": p["title"], "difficulty": p["difficulty"],
            "tags": p["tags"], "time_limit": p["time_limit"], "memory_limit": p["memory_limit"],
            "judge_mode": p.get("judge_mode", "standard"),
        })
    return ok({"items":items, "total":total, "page": page, "page_size": page_size})

@router.get("/{problem_id}")
async def get_problem(problem_id: str, request: Request = None):
    """获取题目详情，需要登录；学生看不到test_cases和spj_code，被禁用用户无法访问"""
    # 检查登录状态
    user_id = request.session.get("user_id") if request else None
    if not user_id:
        return error_resp(401, "not logged in")
    
    from app.repositories.user_repo import get_user_by_id
    user = await get_user_by_id(user_id)
    if not user:
        return error_resp(401, "user not found")
    if not user["is_active"]:
        return error_resp(403, "user is disabled")

    problem = await problem_repo.get_problem_by_id(problem_id)
    if not problem:
        return error_resp(404, "problem not found")
    
    # 学生看不到测试点数据和SPJ源码
    if user["role"] not in ("teacher", "admin"):
        problem.pop("test_cases", None)
        problem.pop("spj_code", None)

    return ok(problem)

@router.post("")
async def create_problem(req: ProblemCreateRequest, user: dict = Depends(RequireRole("teacher","admin"))):
    if await problem_repo.problem_exists(req.id):
        return error_resp(409, "problem id already exists")
    problem = await problem_repo.create_problem(req.model_dump())
    return created_resp(problem, message = "problem created")

@router.put("/{problem_id}")
async def update_problem(problem_id: str, req: ProblemUpdateRequest, user: dict = Depends(RequireRole("teacher","admin"))):
    if not await problem_repo.problem_exists(problem_id):
        return error_resp(404, "problem not found!")
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    problem = await problem_repo.update_problem(problem_id, update_data)
    return ok(problem, message = "problem updated")

@router.delete("/{problem_id}")
async def delete_problem(problem_id: str, user: dict = Depends(RequireRole("teacher", "admin"))):#user是用来查权限的
    if not await problem_repo.delete_problem(problem_id):
        return error_resp(404, "problem not found")
    return ok(message="problem deleted")


# ========== SPJ 管理接口 ==========

class SpjUpdateRequest(BaseModel):
    spj_code: str

@router.put("/{problem_id}/spj")
async def upload_or_replace_spj(problem_id: str, req: SpjUpdateRequest, user: dict = Depends(RequireRole("teacher", "admin"))):
    """上传或替换题目的 SPJ 代码"""
    problem = await problem_repo.get_problem_by_id(problem_id)
    if not problem:
        return error_resp(404, "problem not found")
    if problem.get("judge_mode") != "spj":
        return error_resp(400, "该题目的 judge_mode 不是 spj，请先修改 judge_mode")
    updated = await problem_repo.update_spj_code(problem_id, req.spj_code)
    return ok(updated, message="SPJ updated")

@router.delete("/{problem_id}/spj")
async def delete_spj(problem_id: str, user: dict = Depends(RequireRole("teacher", "admin"))):
    """删除题目的 SPJ 代码"""
    problem = await problem_repo.get_problem_by_id(problem_id)
    if not problem:
        return error_resp(404, "problem not found")
    updated = await problem_repo.update_spj_code(problem_id, None)
    return ok(updated, message="SPJ deleted")

@router.get("/{problem_id}/spj")
async def get_spj(problem_id: str, user: dict = Depends(RequireRole("teacher", "admin"))):
    """获取题目的 SPJ 代码（仅教师/管理员）"""
    problem = await problem_repo.get_problem_by_id(problem_id)
    if not problem:
        return error_resp(404, "problem not found")
    return ok({"spj_code": problem.get("spj_code"), "judge_mode": problem.get("judge_mode")})