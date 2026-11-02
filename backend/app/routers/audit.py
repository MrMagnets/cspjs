"""陶片放逐：管理员操作审计日志。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from deps import require_admin
from models import AuditLog, User
from schemas import AuditLogOut

router = APIRouter(tags=["审计"])


def log_action(
    db: Session,
    admin: User | None,
    action: str,
    target_type: str = "",
    target_id: int | None = None,
    detail: str = "",
) -> None:
    """写入审计日志；由调用方统一 commit。"""
    db.add(
        AuditLog(
            admin_id=admin.id if admin else None,
            action=action[:64],
            target_type=target_type[:32],
            target_id=target_id,
            detail=detail[:1000],
        )
    )


@router.get("/admin/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [
        AuditLogOut(
            id=row.id,
            admin_id=row.admin_id,
            admin_name=row.admin.username if row.admin else "系统",
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            detail=row.detail,
            created_at=row.created_at,
        )
        for row in rows
    ]
