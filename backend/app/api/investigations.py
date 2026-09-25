from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, require_roles
from backend.app.models.auth import User
from backend.app.models.investigation import Investigation, Remediation, Feedback
from backend.app.models.base import UserRole
from backend.app.schemas.investigation import (
    InvestigationResponse,
    RemediationResponse,
    FeedbackCreate,
    FeedbackResponse
)
from agents.remediation_agent.remediation_agent import remediation_agent

router = APIRouter(prefix="/investigations", tags=["Investigations & Remediation"])

@router.get("", response_model=List[InvestigationResponse])
def list_investigations(db: Session = Depends(get_db)):
    return db.query(Investigation).order_by(desc(Investigation.created_at)).all()

@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(investigation_id: str, db: Session = Depends(get_db)):
    inv = db.query(Investigation).filter_by(id=investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return inv

@router.post(
    "/{investigation_id}/remediations/{remediation_id}/approve",
    status_code=status.HTTP_200_OK
)
def approve_remediation(
    investigation_id: str,
    remediation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.INVESTIGATOR]))
):
    """
    Human approval gate:
    Approves and triggers execution of a proposed remediation action.
    Strictly restricted to ADMIN or INVESTIGATOR roles.
    """
    result = remediation_agent.approve_and_execute(
        db=db,
        remediation_id=remediation_id,
        user_id=current_user.id,
        user_role=current_user.role.value
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    fb_in: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits developer feedback on the correctness of an RCA investigation.
    Feeds back into historical learning and model calibration.
    """
    inv = db.query(Investigation).filter_by(id=fb_in.investigation_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    fb = Feedback(
        investigation_id=fb_in.investigation_id,
        user_id=current_user.id,
        is_rca_correct=fb_in.is_rca_correct,
        actual_classification=fb_in.actual_classification,
        comments=fb_in.comments
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
