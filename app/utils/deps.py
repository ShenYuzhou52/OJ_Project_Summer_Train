from fastapi import Request, HTTPException
from app.repositories import user_repo

async def get_current_user(request: Request) -> dict:
    #从Session中获取当前用户，如果没登陆的话抛401，登录了没权限抛403
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail = "not logged in")
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail = "user not found")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail = "user is not authorized")
    return user

class RequireRole:
    def __init__(self,*roles:str):
        self.roles = roles
    
    async def __call__(self, request: Request) -> dict:
        user = await get_current_user(request)
        if user["role"] not in self.roles:
            raise HTTPException(status_code=403, detail="insufficient_permissions")
        return user
    

require_teacher = RequireRole("teacher","admin")
require_admin = RequireRole("admin")

