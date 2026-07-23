from fastapi import APIRouter, Depends, Query
from app.repositories.audit_log_repo import search_audit_logs
from app.utils.deps import RequireRole
from app.utils.response import ok

router = APIRouter(tags=["audit"])


@router.get("/api/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    operator_id: str = None, action: str = None,
    target_id: str = None, start_time: str = None, end_time: str = None,
    user: dict = Depends(RequireRole("admin")),
):
    logs, total = await search_audit_logs(
        page, page_size, operator_id, action, target_id, start_time, end_time
    )
    items = [{
        "id": l["id"], "operator_id": l["operator_id"], "action": l["action"],
        "target_type": l["target_type"], "target_id": l["target_id"],
        "success": bool(l["success"]), "detail": l["detail"], "created_at": l["created_at"],
    } for l in logs]
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})
