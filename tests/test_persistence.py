"""持久化测试：重启后读取、创建备份、恢复成功、损坏备份恢复失败且不破坏现有数据"""
import pytest
import os
import json
import shutil
from httpx import AsyncClient, ASGITransport
from tests.conftest import SAMPLE_PROBLEM

pytestmark = pytest.mark.asyncio


# --- 重启后读取：数据在重新初始化后仍然存在 ---
async def test_data_persists_after_reinit(client: AsyncClient):
    """模拟重启：写入数据后重新 init_db，数据依然存在"""
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": "persist-01"})
    # 模拟重启（重新 init_db）
    from app.repositories.database import init_db
    await init_db()
    # 重新登录后仍可读取
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp = await client.get("/api/problems/persist-01")
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "A+B Problem"


# --- 创建备份 ---
async def test_create_backup(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp = await client.post("/api/admin/backups")
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert "backup_id" in data


# --- 恢复成功 ---
async def test_restore_backup_success(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    # 创建题目
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": "persist-restore"})
    # 创建备份
    resp = await client.post("/api/admin/backups")
    backup_id = resp.json()["data"]["backup_id"]
    # 删除题目
    await client.delete("/api/problems/persist-restore")
    resp_check = await client.get("/api/problems/persist-restore")
    assert resp_check.status_code == 404
    # 恢复备份
    resp2 = await client.post(f"/api/admin/backups/{backup_id}/restore")
    assert resp2.status_code == 200
    # 重新init_db加载恢复后的数据
    from app.repositories.database import init_db
    await init_db()
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    # 题目应恢复
    resp3 = await client.get("/api/problems/persist-restore")
    assert resp3.status_code == 200


# --- 损坏备份恢复失败且不破坏现有数据 ---
async def test_restore_corrupted_backup_fails_safely(client: AsyncClient):
    import app.config as cfg
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    # 创建题目和备份
    await client.post("/api/problems", json={**SAMPLE_PROBLEM, "id": "persist-safe"})
    resp = await client.post("/api/admin/backups")
    backup_id = resp.json()["data"]["backup_id"]
    # 损坏备份（破坏manifest）
    backup_dir = os.path.join(cfg.BACKUP_DIR, backup_id)
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        f.write("NOT VALID JSON {{{")
    # 尝试恢复损坏备份
    resp2 = await client.post(f"/api/admin/backups/{backup_id}/restore")
    assert resp2.status_code in (400, 500)
    # 现有数据应完好
    from app.repositories.database import init_db
    await init_db()
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp3 = await client.get("/api/problems/persist-safe")
    assert resp3.status_code == 200
    assert resp3.json()["data"]["title"] == "A+B Problem"


async def test_restore_nonexistent_backup(client: AsyncClient):
    await client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    resp = await client.post("/api/admin/backups/nonexistent_backup_id/restore")
    assert resp.status_code == 404