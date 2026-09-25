from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.security import require_roles
from backend.app.models.auth import User
from backend.app.models.base import UserRole
from backend.app.models.investigation import AuditLog
from backend.app.schemas.investigation import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit Trail"])

@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.INVESTIGATOR]))
):
    """
    Returns audit trail records for compliance, tracking user actions and mutations.
    Restricted to ADMIN and INVESTIGATOR roles.
    """
    return db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit).all()
