from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user
from backend.app.models.auth import User
from backend.app.models.failure import Failure, Fingerprint
from backend.app.models.investigation import Investigation
from backend.app.models.base import FailureClassification, SeverityLevel
from backend.app.schemas.failure import FailureResponse, FingerprintResponse, IngestExecutionRequest
from backend.app.schemas.investigation import InvestigationResponse
from backend.app.services.ingestion_service import IngestionService
from ingestion.log_normalizer.junit_parser import parse_junit_xml, parse_test_json
from agents.orchestrator.orchestrator import TriageOrchestrator

router = APIRouter(prefix="/failures", tags=["Failures & Triage"])

@router.get("", response_model=List[FailureResponse])
def get_failures(
    classification: Optional[FailureClassification] = None,
    severity: Optional[SeverityLevel] = None,
    test_run_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Failure)
    if classification:
        q = q.filter(Failure.classification == classification)
    if severity:
        q = q.filter(Failure.severity == severity)
    if test_run_id:
        q = q.filter(Failure.test_run_id == test_run_id)
    return q.order_by(desc(Failure.created_at)).limit(limit).all()

@router.get("/fingerprints", response_model=List[FingerprintResponse])
def get_fingerprints(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return db.query(Fingerprint).order_by(desc(Fingerprint.occurrence_count)).limit(limit).all()

@router.get("/{failure_id}", response_model=FailureResponse)
def get_failure_detail(failure_id: str, db: Session = Depends(get_db)):
    failure = db.query(Failure).filter_by(id=failure_id).first()
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")
    return failure

@router.post("/{failure_id}/investigate", response_model=InvestigationResponse)
def trigger_investigation(
    failure_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Executes the multi-agent investigation workflow for the selected failure:
    Log Agent -> History Agent -> Git Agent -> Component/Owner Agent ->
    Evidence Agent -> RCA Agent (H1..H7) -> Remediation Agent.
    """
    failure = db.query(Failure).filter_by(id=failure_id).first()
    if not failure:
        raise HTTPException(status_code=404, detail="Failure not found")

    user_id = current_user.id if current_user else None
    orchestrator = TriageOrchestrator(db)
    try:
        investigation = orchestrator.run_investigation(failure_id=failure.id, assigned_user_id=user_id)
        return investigation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Investigation workflow failed: {str(e)}")

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_execution(request: IngestExecutionRequest, db: Session = Depends(get_db)):
    """
    Ingests JUnit XML or JSON test execution report directly into the platform.
    """
    cases = []
    if request.junit_xml:
        cases = parse_junit_xml(request.junit_xml)
    elif request.json_report:
        cases = parse_test_json(request.json_report)
    else:
        raise HTTPException(status_code=400, detail="Either junit_xml or json_report must be provided.")

    service = IngestionService(db)
    result = service.ingest_test_execution_record(
        repo_name=request.repository_name,
        pipeline_name=request.pipeline_name,
        commit_sha=request.commit_sha,
        branch=request.branch,
        test_case_records=cases,
        runner_os=request.runner_os,
        runner_version=request.runner_version
    )
    return result
