import pytest
from backend.app.core.database import SessionLocal, init_db
from backend.app.models import Failure, Test, TestRun, Build, Pipeline, Repository, User, UserRole, RemediationStatus
from backend.app.models.base import FailureClassification, SeverityLevel
from agents.tools.allowlisted_tools import AllowlistedTools
from agents.orchestrator.orchestrator import TriageOrchestrator
from agents.remediation_agent.remediation_agent import remediation_agent

def test_agent_tools_and_orchestrator():
    init_db()
    db = SessionLocal()

    # Create dummy user
    user = db.query(User).filter_by(username="admin_user").first()
    if not user:
        user = User(
            username="admin_user",
            email="admin_user@example.com",
            hashed_password="hash",
            role=UserRole.ADMIN
        )
        db.add(user)
        db.commit()

    # Find or create a failure
    failure = db.query(Failure).first()
    if not failure:
        from backend.app.services.ingestion_service import IngestionService
        from ingestion.log_normalizer.junit_parser import parse_junit_xml
        xml = """<testsuites><testsuite name="unit" tests="1"><testcase classname="test_core" name="test_order"><failure message="AssertionError: 500 != 200" type="AssertionError">File 'app/order.py', line 12\nassert status == 200</failure></testcase></testsuite></testsuites>"""
        cases = parse_junit_xml(xml)
        service = IngestionService(db)
        service.ingest_test_execution_record("demo-repo", "CI", "sha123", "main", cases)
        failure = db.query(Failure).first()
    assert failure is not None

    # Test tools
    tools = AllowlistedTools(db)
    test_hist = tools.get_test_history(failure.test_id)
    assert test_hist["status"] == "success"

    flaky_info = tools.calculate_flakiness(failure.test_id)
    assert flaky_info["status"] == "success"

    # Run full orchestration
    orchestrator = TriageOrchestrator(db)
    inv = orchestrator.run_investigation(failure.id, assigned_user_id=user.id)
    assert inv is not None
    assert inv.status.value == "RCA_READY"
    assert inv.evidence_bundle is not None
    assert len(inv.hypotheses_evaluated) == 7

    # Check proposed remediation
    assert len(inv.remediations) > 0
    rem = inv.remediations[0]
    assert rem.status == RemediationStatus.PENDING_APPROVAL

    # Test Human Approval Gate
    res = remediation_agent.approve_and_execute(
        db=db,
        remediation_id=rem.id,
        user_id=user.id,
        user_role=user.role.value
    )
    assert res["success"] is True
    assert res["status"] in ["APPROVED", "EXECUTED"]

    db.close()

def test_rca_agent_refuses_conclusion_with_empty_or_missing_evidence_ids():
    """
    Regression test enforcing that the RCA agent refuses to output a conclusion
    when evidence_ids or evidence_bundle is empty or missing (agents must not invent evidence).
    """
    from agents.rca_agent.hypothesis_evaluator import hypothesis_evaluator

    # Case 1: Empty evidence bundle dictionary
    with pytest.raises(ValueError, match="RCA Agent refuses to output a conclusion"):
        hypothesis_evaluator.evaluate(
            evidence_bundle={},
            classification="REGRESSION",
            error_type="AssertionError"
        )

    # Case 2: Bundle with empty valid_evidence_ids list
    with pytest.raises(ValueError, match="evidence_ids is missing or empty"):
        hypothesis_evaluator.evaluate(
            evidence_bundle={"valid_evidence_ids": [], "evidence_items": []},
            classification="REGRESSION",
            error_type="AssertionError"
        )

    # Case 3: Bundle missing evidence_ids entirely
    with pytest.raises(ValueError, match="evidence_ids is missing or empty"):
        hypothesis_evaluator.evaluate(
            evidence_bundle={"evidence_items": [{"evidence_id": "EV-01", "evidence_type": "GIT"}]},
            classification="REGRESSION",
            error_type="AssertionError"
        )

    # Case 4: Bundle with valid_evidence_ids but empty evidence_items
    with pytest.raises(ValueError, match="evidence_items is empty"):
        hypothesis_evaluator.evaluate(
            evidence_bundle={"valid_evidence_ids": ["EV-01"], "evidence_items": []},
            classification="REGRESSION",
            error_type="AssertionError"
        )

