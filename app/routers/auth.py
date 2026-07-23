from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel, Field
from app.models.user import UserRegisterRequest, UserLoginRequest
from app.services.auth_service import register, login, verify_password
from app.repositories import user_repo
from app.utils.deps import get_current_user
from app.utils.response import ok, error_resp, created_resp
import bcrypt

router = APIRouter(prefix = "/api/auth", tags = ["auth"])

@router.post("/register") #用户注册接口
async def register_endpoint(req: UserRegisterRequest):
    result = await register(req.username, req.password)
    if isinstance(result, str):
        if "exists" in result: #已经存在，报409错误
            return error_resp(409, result)
        return error_resp(400, result)
    return created_resp({"id": result["id"], "username": result["username"], "role": result["role"]})


@router.post("/login")
async def login_endpoint(req: UserLoginRequest, request: Request):
    result = await login(req.username, req.password)
    if isinstance(result, str):
        if "disabled" in result:
            return error_resp(403, result)
        return error_resp(401, "invalid credentials")
    request.session["user_id"] = result["id"] #把用户ID写入服务器端的session,于是之后的请求都能拿到这个值
    return ok({"id": result["id"], "username": result["username"], "role": result["role"]})

@router.post("/logout") #post改变服务器状态
async def logout_endpoint(request: Request):
    request.session.clear()
    return ok(message="logged out")

@router.get("/me")
async def me_endpoint(request: Request): #获取当前用户信息
    user_id = request.session.get("user_id")
    if not user_id:
        return error_resp(401, "not logged in")
    from app.repositories.user_repo import get_user_by_id
    user = await get_user_by_id(user_id)
    if not user:
        request.session.clear()
        return error_resp(401, "user not found")
    if not user["is_active"]:
        request.session.clear()
        return error_resp(403, "account is disabled")
    return ok({
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "is_active": bool(user["is_active"]),
    })


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


@router.post("/change-password")
async def change_password_endpoint(req: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    # 验证旧密码
    if not verify_password(req.old_password, user["password_hash"]):
        return error_resp(400, "old password is incorrect")
    # 生成新密码哈希
    new_hash = bcrypt.hashpw(req.new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    await user_repo.update_password(user["id"], new_hash)
    return ok(message="password changed successfully")