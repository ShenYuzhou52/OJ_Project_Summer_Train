import bcrypt
from app.repositories import user_repo
from app.repositories.audit_log_repo import create_audit_log

async def register(username: str, password: str) -> dict | str:
    # 注册服务，成功返回用户信息，失败返回错误信息
    if await user_repo.username_exists(username):
        return "username already exists"
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = await user_repo.create_user(username, password_hash, role="student")
    return user

async def login(username: str, password: str) -> dict | str:
    user = await user_repo.get_user_by_username(username)
    if not user:
        return "invalid credentials"
    if not user["is_active"]:
        return "user disabled"
    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return "invalid credentials"
    return user

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))