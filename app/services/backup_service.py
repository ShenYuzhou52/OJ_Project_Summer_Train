import os
import shutil
import json
import aiosqlite
import app.config as _cfg
from app.utils.time_utils import now_utc


async def create_backup(operator_id: str) -> dict:
    """创建备份"""
    timestamp = now_utc().replace(":", "").replace("-", "").replace("T", "_").replace("Z", "")
    backup_id = f"backup_{timestamp}"
    backup_dir = os.path.join(_cfg.BACKUP_DIR, backup_id)
    os.makedirs(backup_dir, exist_ok=True)

    # WAL checkpoint：确保所有 WAL 内容写入主数据库文件再备份
    from app.repositories.database import get_db
    db = await get_db()
    try:
        await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        await db.close()

    # 复制数据库文件
    db_backup_path = os.path.join(backup_dir, "oj.db")
    shutil.copy2(_cfg.DB_PATH, db_backup_path)

    # 写入 manifest
    manifest = {
        "created_at": now_utc(),
        "storage_type": "sqlite",
        "files": ["oj.db"]
    }
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 写入 backups 表 延迟导入数据库连接函数，避免模块加载时产生循环依赖
    from app.repositories.database import get_db
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO backups (backup_id, created_at) VALUES (?, ?)",
            (backup_id, manifest["created_at"])
        )
        await db.commit()
    finally:
        await db.close()

    from app.repositories.audit_log_repo import create_audit_log
    await create_audit_log(operator_id, "CREATE_BACKUP", "backup", backup_id)

    return {"backup_id": backup_id, "created_at": manifest["created_at"]}


async def list_backups() -> list[dict]:
    """列出所有备份"""
    backups = []
    if not os.path.exists(_cfg.BACKUP_DIR):
        return backups
    for name in sorted(os.listdir(_cfg.BACKUP_DIR), reverse=True):
        manifest_path = os.path.join(_cfg.BACKUP_DIR, name, "manifest.json") # 拼接该目录对应的 manifest 文件路径
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            backups.append({"backup_id": name, "created_at": manifest["created_at"]})
    return backups


async def restore_backup(backup_id: str, operator_id: str) -> str | None:
    """恢复备份，成功返回 None，失败返回错误消息"""
    backup_dir = os.path.join(_cfg.BACKUP_DIR, backup_id)
    if not os.path.exists(backup_dir):
        return "backup not found"

    # 校验 manifest
    manifest_path = os.path.join(backup_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return "manifest not found"

    with open(manifest_path, "r", encoding="utf-8") as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError:
            return "manifest corrupted"

    # 校验所需文件
    for fname in manifest.get("files", []):
        if not os.path.exists(os.path.join(backup_dir, fname)):
            return f"missing file: {fname}"

    # 先备份当前数据为安全副本
    safety_copy = _cfg.DB_PATH + ".safety"
    if os.path.exists(_cfg.DB_PATH):
        shutil.copy2(_cfg.DB_PATH, safety_copy)

    try:
        # 复制备份的数据库
        db_backup = os.path.join(backup_dir, "oj.db")
        shutil.copy2(db_backup, _cfg.DB_PATH) # 用备份数据库覆盖当前正在使用的数据库文件

        from app.repositories.audit_log_repo import create_audit_log
        await create_audit_log(operator_id, "RESTORE_BACKUP", "backup", backup_id)

        # 删除安全副本
        if os.path.exists(safety_copy):
            os.remove(safety_copy)
        return None
    except Exception as e:
        # 恢复失败，还原安全副本
        if os.path.exists(safety_copy):
            shutil.copy2(safety_copy, _cfg.DB_PATH)
            os.remove(safety_copy)
        return f"restore failed: {str(e)}"
