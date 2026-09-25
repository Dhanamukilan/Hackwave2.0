import pytest
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app, seed_default_admin
from backend.app.core.database import init_db, SessionLocal
from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.auth import User
from backend.app.models.base import UserRole, RemediationStatus
from backend.app.models.investigation import Investigation, Remediation
from backend.app.models.failure import Failure

BOOTSTRAP_TEST_PASSWORD = "BootstrapSecret123!"

@pytest.fixture(scope="module")
def client():
    settings.ADMIN_BOOTSTRAP_PASSWORD = BOOTSTRAP_TEST_PASSWORD
    init_db()

    # Reset any existing admin user to test bootstrap state
    db = SessionLocal()
    admin = db.query(User).filter_by(username="admin").first()
    if admin:
        admin.hashed_password = hash_password(BOOTSTRAP_TEST_PASSWORD)
        admin.must_change_password = True
        db.commit()
    db.close()

    seed_default_admin()
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_regression_old_hardcoded_admin_credentials_fail(client):
    """
    Regression test: asserts that logging in with the old hardcoded default credentials
    (admin / AdminPass123!) fails strictly with 401 Unauthorized.
    """
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "AdminPass123!"}
    )
    assert res.status_code == 401
    assert "Incorrect username or password" in res.json().get("detail", "")

def test_bootstrap_admin_flow_and_forced_password_change(client):
    """
    Verifies that:
    1. Bootstrap admin logs in with configured bootstrap password.
    2. must_change_password is True.
    3. Calling non-auth endpoints is strictly blocked with HTTP 403.
    4. Changing password clears must_change_password.
    5. Non-auth endpoints become accessible.
    """
    # 1. Login with bootstrap credentials
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": BOOTSTRAP_TEST_PASSWORD}
    )
    assert res.status_code == 200
    data = res.json()
    token = data["access_token"]
    assert data["user"]["must_change_password"] is True

    # 2. Verify non-auth endpoint is blocked
    blocked_res = client.get(
        "/api/v1/failures",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert blocked_res.status_code == 403
    assert "Password change required" in blocked_res.json()["detail"]

    # 3. Auth endpoint /me is allowed
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "admin"

    # 4. Change password
    new_password = "NewPermanentAdminPass456!"
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": BOOTSTRAP_TEST_PASSWORD, "new_password": new_password}
    )
    assert change_res.status_code == 200
    assert change_res.json()["must_change_password"] is False

    # 5. Non-auth endpoint now succeeds with unblocked access
    unblocked_res = client.get(
        "/api/v1/failures",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert unblocked_res.status_code == 200

def test_human_approval_gate_rbac(client):
    """
    Verifies human approval gate:
    1. Remediation is in PENDING_APPROVAL.
    2. Non-privileged DEVELOPER role receives HTTP 403 when attempting approval.
    3. ADMIN role successfully approves remediation, transitioning to APPROVED / EXECUTED.
    """
    db = SessionLocal()
    failure = db.query(Failure).first()
    assert failure is not None

    inv = Investigation(
        failure_id=failure.id,
        rca_summary="Test investigation",
        confidence="HIGH"
    )
    db.add(inv)
    db.flush()

    rem = Remediation(
        investigation_id=inv.id,
        proposed_action="Retry test run",
        action_type="RETRY_PIPELINE",
        status=RemediationStatus.PENDING_APPROVAL
    )
    db.add(rem)
    db.commit()
    rem_id = rem.id
    inv_id = inv.id

    # Create a test developer user
    dev_username = f"dev_{uuid.uuid4().hex[:6]}"
    dev_pw = "DevPassword123!"
    dev_user = User(
        username=dev_username,
        email=f"{dev_username}@example.com",
        hashed_password=hash_password(dev_pw),
        role=UserRole.DEVELOPER,
        must_change_password=False
    )
    db.add(dev_user)
    db.commit()
    db.close()

    # Developer logs in
    dev_login = client.post(
        "/api/v1/auth/login",
        data={"username": dev_username, "password": dev_pw}
    )
    assert dev_login.status_code == 200
    dev_token = dev_login.json()["access_token"]

    # Developer attempts approval -> 403 Forbidden
    approve_fail = client.post(
        f"/api/v1/investigations/{inv_id}/remediations/{rem_id}/approve",
        headers={"Authorization": f"Bearer {dev_token}"}
    )
    assert approve_fail.status_code == 403

    # Admin logs in with updated password
    admin_login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "NewPermanentAdminPass456!"}
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    # Admin approves -> 200 OK
    approve_ok = client.post(
        f"/api/v1/investigations/{inv_id}/remediations/{rem_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert approve_ok.status_code == 200
    assert approve_ok.json()["status"] in ["APPROVED", "EXECUTED"]

def test_ml_cold_start_metrics(client):
    res = client.get("/api/v1/ml/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["provenance_label"] == "[synthetic benchmark]"
    assert "classification_metrics" in data

def test_pipelines_and_builds_endpoints(client):
    res = client.get("/api/v1/repositories")
    assert res.status_code == 200

    builds_res = client.get("/api/v1/builds")
    assert builds_res.status_code == 200

def test_failures_listing(client):
    res = client.get("/api/v1/failures")
    assert res.status_code == 200
    failures = res.json()
    assert isinstance(failures, list)
