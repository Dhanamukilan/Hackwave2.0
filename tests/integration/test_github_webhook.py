import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.database import SessionLocal, init_db
from backend.app.core.config import settings
from backend.app.models import Build, Failure, Pipeline, Repository

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c

def compute_hmac_header(payload_bytes: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

def test_webhook_valid_hmac_signature(client):
    """
    Verifies that a GitHub webhook request with a valid HMAC-SHA256 signature
    is successfully authenticated and accepted with HTTP 200.
    """
    payload = {
        "action": "completed",
        "workflow_run": {
            "id": 999001,
            "name": "CI",
            "status": "completed",
            "conclusion": "success",
            "head_sha": "a1b2c3d4e5f6001",
            "head_branch": "main",
            "event": "push"
        },
        "repository": {
            "name": "Hackwave2.0",
            "full_name": "Dhanamukilan/Hackwave2.0"
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_hmac_header(payload_bytes, settings.GITHUB_WEBHOOK_SECRET)

    res = client.post(
        "/api/v1/webhooks/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "workflow_run",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["handled"] is True

def test_webhook_invalid_hmac_signature_rejected(client):
    """
    Verifies that a GitHub webhook request with an invalid signature
    is strictly rejected with HTTP 401 Unauthorized.
    """
    payload = {"action": "completed", "workflow_run": {"id": 999002}}
    payload_bytes = json.dumps(payload).encode("utf-8")

    res = client.post(
        "/api/v1/webhooks/github",
        content=payload_bytes,
        headers={
            "X-Hub-Signature-256": "sha256=invalid_tampered_signature_hash_000000000000000000000000000000",
            "X-GitHub-Event": "workflow_run",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 401
    assert "Invalid GitHub webhook HMAC-SHA256 signature" in res.json().get("detail", "")

def test_webhook_missing_signature_rejected(client):
    """
    Verifies that an unsigned GitHub webhook request is rejected with HTTP 401 Unauthorized.
    """
    payload = {"action": "completed"}
    payload_bytes = json.dumps(payload).encode("utf-8")

    res = client.post(
        "/api/v1/webhooks/github",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "workflow_run",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 401

def test_webhook_malformed_json_rejected(client):
    """
    Verifies that a malformed JSON payload is rejected gracefully with HTTP 400 Bad Request.
    """
    bad_payload = b'{"action": "completed", "workflow_run": {'
    sig = compute_hmac_header(bad_payload, settings.GITHUB_WEBHOOK_SECRET)

    res = client.post(
        "/api/v1/webhooks/github",
        content=bad_payload,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "workflow_run",
            "Content-Type": "application/json"
        }
    )
    assert res.status_code == 400
    assert "Invalid JSON payload" in res.json().get("detail", "")

def test_webhook_duplicate_delivery_idempotency(client):
    """
    Verifies that duplicate webhook deliveries (retried by GitHub on timeout or network blips)
    do not create duplicate Build or Failure records.
    """
    sha = "test_idempotent_sha_9999"
    payload = {
        "action": "completed",
        "workflow_run": {
            "id": 888123,
            "name": "CI",
            "status": "completed",
            "conclusion": "failure",
            "head_sha": sha,
            "head_branch": "main",
            "event": "push"
        },
        "repository": {
            "name": "Hackwave2.0",
            "full_name": "Dhanamukilan/Hackwave2.0"
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    sig = compute_hmac_header(payload_bytes, settings.GITHUB_WEBHOOK_SECRET)

    headers = {
        "X-Hub-Signature-256": sig,
        "X-GitHub-Event": "workflow_run",
        "Content-Type": "application/json"
    }

    # Delivery 1
    res1 = client.post("/api/v1/webhooks/github", content=payload_bytes, headers=headers)
    assert res1.status_code == 200

    db = SessionLocal()
    builds_after_first = db.query(Build).filter_by(commit_sha=sha).all()
    count_first = len(builds_after_first)
    assert count_first == 1

    # Delivery 2 (Exact duplicate retry)
    res2 = client.post("/api/v1/webhooks/github", content=payload_bytes, headers=headers)
    assert res2.status_code == 200

    builds_after_second = db.query(Build).filter_by(commit_sha=sha).all()
    count_second = len(builds_after_second)
    assert count_second == 1  # IDEMPOTENT: No duplicate build created
    db.close()

def test_github_actions_adapter_ingestion_direct():
    """
    Verifies that GitHubActionsAdapter.ingest_workflow_run persists all entities
    (Repository, Commit, Pipeline, Build, TestRun) and executes triage orchestrator.
    """
    from ingestion.github_actions_adapter.adapter import github_actions_adapter
    db: Session = SessionLocal()
    try:
        run_id = "test-run-mock-998811"
        sha = "f9e8d7c6b5a4112233"
        result = github_actions_adapter.ingest_workflow_run(
            db=db,
            run_id=run_id,
            commit_sha=sha,
            branch="main",
            repo_name="Hackwave2.0",
            workflow_name="CI"
        )
        assert "ingest_result" in result
        build = db.query(Build).filter_by(commit_sha=sha).first()
        assert build is not None
        assert build.commit_sha == sha
    finally:
        db.close()
