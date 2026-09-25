import pytest
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal, init_db
from backend.app.models import Build, TestRun, Test, Failure, Investigation
from ingestion.base_adapter import CIAdapter
from ingestion.jenkins_adapter.adapter import JenkinsAdapter, jenkins_adapter

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_jenkins_adapter_ci_interface():
    """
    Verifies that JenkinsAdapter correctly subclasses the shared CIAdapter interface.
    """
    assert issubclass(JenkinsAdapter, CIAdapter)
    assert hasattr(jenkins_adapter, "fetch_workflow_run")
    assert hasattr(jenkins_adapter, "fetch_run_jobs")
    assert hasattr(jenkins_adapter, "fetch_job_logs")
    assert hasattr(jenkins_adapter, "fetch_commit_details")
    assert hasattr(jenkins_adapter, "trigger_rerun")

def test_jenkins_adapter_end_to_end_ingestion(db_session: Session):
    """
    Verifies that JenkinsAdapter.ingest_jenkins_build normalizes Jenkins pipeline
    results into standard Build, TestRun, Test, Failure, and Investigation entities.
    """
    job_name = "test-jenkins-job-99"
    build_no = "105"
    sha = "jenkins-sha-test-105"

    result = jenkins_adapter.ingest_jenkins_build(
        db=db_session,
        job_name=job_name,
        build_number=build_no,
        commit_sha=sha,
        branch="main",
        repo_name="Hackwave2.0"
    )

    assert result["ci_provider"] == "jenkins"
    assert "ingest_result" in result
    ingest = result["ingest_result"]

    # 1. Build record check
    build = db_session.query(Build).filter_by(id=ingest["build_id"]).first()
    assert build is not None
    assert build.commit_sha == sha
    assert build.pipeline.provider == "jenkins"

    # 2. TestRun record check
    test_run = db_session.query(TestRun).filter_by(id=ingest["test_run_id"]).first()
    assert test_run is not None
    assert test_run.runner_os == "linux-jenkins-agent"

    # 3. Failure & Investigation check
    assert len(ingest["failures_created"]) >= 1
    fail_id = ingest["failures_created"][0]
    failure = db_session.query(Failure).filter_by(id=fail_id).first()
    assert failure is not None

    inv = db_session.query(Investigation).filter_by(failure_id=fail_id).first()
    assert inv is not None
    assert inv.status.value in ("RCA_READY", "rca_ready", "TRIAGED", "triaged")
    assert inv.confidence.value in ("HIGH", "high", "MEDIUM", "medium")
    assert len(inv.evidence_bundle.get("valid_evidence_ids", [])) >= 1

def test_jenkins_schema_parity_with_github(db_session: Session):
    """
    Verifies that Jenkins and GitHub Actions produce identical schemas
    and can both be queried using the exact same database models.
    """
    jenkins_builds = db_session.query(Build).join(Build.pipeline).filter_by(provider="jenkins").all()
    gh_builds = db_session.query(Build).join(Build.pipeline).filter_by(provider="github_actions").all()

    # Both providers must write into the exact same database table
    assert len(jenkins_builds) >= 1
    assert len(gh_builds) >= 1
    for b in jenkins_builds + gh_builds:
        assert hasattr(b, "id")
        assert hasattr(b, "commit_sha")
        assert hasattr(b, "status")
        assert hasattr(b, "test_runs")
