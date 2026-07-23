from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from app.repositories import user_repo
from app.models.user import UserUpdateRequest
from app.services.backup_service import create_backup, list_backups, restore_backup
from app.repositories.audit_log_repo import create_audit_log
from app.utils.deps import RequireRole
from app.utils.response import ok, error_resp, created_resp
import bcrypt

router = APIRouter(prefix="/api", tags=["admin"])


# --- 用户管理 ---
@router.get("/users")
async def list_users(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                      username: Optional[str] = Query(None), role: Optional[str] = Query(None),
                      is_active: Optional[bool] = Query(None),
                      user: dict = Depends(RequireRole("admin"))):
    try:
        users, total = await user_repo.list_users(page, page_size, username=username, role=role, is_active=is_active)
        items = [{
            "id": u["id"], "username": u["username"], "role": u["role"],
            "is_active": bool(u["is_active"]), "created_at": u["created_at"], "updated_at": u["updated_at"],
        } for u in users]
        return ok({"items": items, "total": total, "page": page, "page_size": page_size})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return error_resp(500, "internal server error")

# 注册 GET /api/users/{user_id} 接口。
@router.get("/users/{user_id}")
async def get_user(user_id: str, user: dict = Depends(RequireRole("admin"))): # 从url中解析user_id
    target = await user_repo.get_user_by_id(user_id)
    if not target:
        return error_resp(404, "user not found")
    return ok({
        "id": target["id"], "username": target["username"], "role": target["role"],
        "is_active": bool(target["is_active"]), "created_at": target["created_at"], "updated_at": target["updated_at"],
    })


@router.put("/users/{user_id}")
async def update_user(user_id: str, req: UserUpdateRequest, user: dict = Depends(RequireRole("admin"))):
    target = await user_repo.get_user_by_id(user_id)
    if not target:
        return error_resp(404, "user not found")
    # 不允许禁用自己
    if req.is_active is False and user_id == user["id"]:
        return error_resp(400, "cannot disable yourself")

    role = req.role.value if req.role else None
    updated = await user_repo.update_user(user_id, role, req.is_active)

    # 审计日志 - 按优先级：禁用 > 角色修改 > 启用 > 其他
    if req.is_active is False:
        action = "DISABLE_USER"
    elif req.role:
        action = "UPDATE_USER_ROLE"
    elif req.is_active is True:
        action = "ENABLE_USER"
    else:
        action = "UPDATE_USER_INFO"
    await create_audit_log(user["id"], action, "user", user_id)

    return ok({
        "id": updated["id"], "username": updated["username"], "role": updated["role"],
        "is_active": bool(updated["is_active"]),
    }, message="user updated")


# --- 管理员重置用户密码 ---
class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8)


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, req: ResetPasswordRequest, user: dict = Depends(RequireRole("admin"))):
    target = await user_repo.get_user_by_id(user_id)
    if not target:
        return error_resp(404, "user not found")
    new_hash = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    await user_repo.update_password(user_id, new_hash)
    await create_audit_log(user["id"], "RESET_USER_PASSWORD", "user", user_id)
    return ok(message="password reset successfully")


# --- 备份 ---
@router.post("/admin/backups")
async def create_backup_endpoint(user: dict = Depends(RequireRole("admin"))):
    result = await create_backup(user["id"])
    return created_resp(result, message="backup created")


@router.get("/admin/backups")
async def list_backups_endpoint(user: dict = Depends(RequireRole("admin"))):
    backups = await list_backups()
    return ok(backups)


@router.post("/admin/backups/{backup_id}/restore")
async def restore_backup_endpoint(backup_id: str, user: dict = Depends(RequireRole("admin"))):
    err = await restore_backup(backup_id, user["id"])
    if err:
        if "not found" in err:
            return error_resp(404, err)
        return error_resp(500, err)
    return ok(message="backup restored")