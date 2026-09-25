import sys
import os
import secrets
from datetime import datetime, timedelta

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.core.config import settings
from backend.app.core.database import SessionLocal, init_db
from backend.app.core.security import hash_password
from backend.app.models import (
    User, Repository, Pipeline, Build, TestRun, Test,
    Fingerprint, Failure, Commit, ChangedFile, Component,
    Owner, Deployment, Prediction, Investigation, Remediation,
    Feedback, AuditLog, UserRole, BuildStatus, FailureClassification,
    SeverityLevel, RCAConfidence, InvestigationStatus, RemediationStatus
)
from database.vector_store.qdrant_client import vector_store
from backend.app.services.ingestion_service import generate_dense_embedding

def seed_all():
    print("Initializing database...")
    init_db()
    db = SessionLocal()

    print("Seeding owners and components...")
    # Owners
    sec_owner = Owner(name="Alex Rivera", email="alex.rivera@example.com", team_name="Security & Auth")
    pay_owner = Owner(name="Elena Rostova", email="elena.rostova@example.com", team_name="Payments & Billing")
    plat_owner = Owner(name="Marcus Chen", email="marcus.chen@example.com", team_name="Core Platform")
    db.add_all([sec_owner, pay_owner, plat_owner])
    db.flush()

    # Components
    comp_auth = Component(name="Authentication Service", description="User login, OAuth, and RBAC", lead_owner_id=sec_owner.id)
    comp_pay = Component(name="Payment Gateway", description="Stripe/PayPal charge execution", lead_owner_id=pay_owner.id)
    comp_plat = Component(name="Platform Core API", description="Core data routing and services", lead_owner_id=plat_owner.id)
    db.add_all([comp_auth, comp_pay, comp_plat])
    db.flush()

    # Users
    admin_user = db.query(User).filter_by(username="admin").first()
    if not admin_user:
        admin_pw = settings.ADMIN_BOOTSTRAP_PASSWORD or secrets.token_urlsafe(16)
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=hash_password(admin_pw),
            role=UserRole.ADMIN,
            must_change_password=True
        )
        db.add(admin_user)
        db.flush()

    # Repository & Pipeline
    repo = Repository(
        name="demo-microservices-app",
        full_name="example-org/demo-microservices-app",
        default_branch="main",
        clone_url="https://github.com/example-org/demo-microservices-app.git"
    )
    db.add(repo)
    db.flush()

    pipeline = Pipeline(
        repository_id=repo.id,
        name="Main CI/CD Pipeline",
        workflow_path=".github/workflows/ci.yml",
        provider="github_actions"
    )
    db.add(pipeline)
    db.flush()

    print("Seeding commits...")
    c1 = Commit(
        repository_id=repo.id,
        sha="a8f190c2e34b",
        author_name="Elena Rostova",
        author_email="elena.rostova@example.com",
        message="feat(payment): optimize charge transaction with strict validation",
        branch="main",
        committed_at=datetime.utcnow() - timedelta(hours=3)
    )
    db.add(c1)
    db.flush()

    cf1 = ChangedFile(
        commit_id=c1.id,
        file_path="services/payment/gateway.py",
        change_type="modified",
        additions=45,
        deletions=12,
        patch_summary="@@ -80,6 +80,12 @@ def process_payment(amount):\n- if amount <= 0:\n+ if amount < 100: raise ValueError('Minimum charge is 100 cents')"
    )
    db.add(cf1)
    db.flush()

    # Deployments
    d1 = Deployment(
        service_id="payment-service",
        environment="production",
        commit_sha=c1.sha,
        status="SUCCESS",
        deployed_at=datetime.utcnow() - timedelta(hours=4)
    )
    db.add(d1)
    db.flush()

    print("Seeding Scenario 01: Genuine Code Regression...")
    b1 = Build(
        pipeline_id=pipeline.id,
        commit_sha=c1.sha,
        branch="main",
        build_number=101,
        status=BuildStatus.FAILURE,
        trigger="push",
        started_at=datetime.utcnow() - timedelta(hours=2, minutes=50),
        completed_at=datetime.utcnow() - timedelta(hours=2, minutes=45),
        duration_seconds=300.0
    )
    db.add(b1)
    db.flush()

    tr1 = TestRun(
        build_id=b1.id,
        runner_os="ubuntu-latest",
        runner_version="22.04",
        total_tests=45,
        passed_tests=44,
        failed_tests=1,
        started_at=datetime.utcnow() - timedelta(hours=2, minutes=49),
        completed_at=datetime.utcnow() - timedelta(hours=2, minutes=45)
    )
    db.add(tr1)
    db.flush()

    test1 = Test(
        repository_id=repo.id,
        name="test_small_amount_charge",
        suite_name="services.payment.test_gateway",
        file_path="tests/test_payment_gateway.py",
        line_number=54,
        flakiness_score=0.05,
        failure_rate=0.10,
        run_count=35
    )
    db.add(test1)
    db.flush()

    fp1 = Fingerprint(
        hash_value="fp_assertion_500_expected_200_payment",
        error_type="AssertionError",
        normalized_message="AssertionError: assert 500 == 200 in test_small_amount_charge",
        location="tests/test_payment_gateway.py:54",
        occurrence_count=1,
        first_seen_at=datetime.utcnow() - timedelta(hours=2, minutes=45),
        last_seen_at=datetime.utcnow() - timedelta(hours=2, minutes=45)
    )
    db.add(fp1)
    db.flush()

    fail1 = Failure(
        test_run_id=tr1.id,
        test_id=test1.id,
        fingerprint_id=fp1.id,
        error_type="AssertionError",
        raw_message="AssertionError: assert 500 == 200 in process_payment(amount=50)",
        normalized_message="AssertionError: assert 500 == 200 in process_payment(amount=<NUM>)",
        raw_stack_trace="File \"tests/test_payment_gateway.py\", line 54, in test_small_amount_charge\nassert res.status_code == 200",
        normalized_stack_trace="File \"tests/test_payment_gateway.py\", line 54, in test_small_amount_charge\nassert res.status_code == 200",
        classification=FailureClassification.REGRESSION,
        classification_confidence=0.96,
        flakiness_score=0.05,
        regression_prob=0.94,
        severity=SeverityLevel.HIGH,
        created_at=datetime.utcnow() - timedelta(hours=2, minutes=45)
    )
    db.add(fail1)
    db.flush()

    vector_store.insert_failure_embedding(
        point_id=fail1.id,
        vector=generate_dense_embedding(f"{fail1.error_type} {fail1.normalized_message}"),
        payload={"fingerprint_id": fp1.id, "failure_id": fail1.id, "test_id": test1.id, "classification": fail1.classification.value}
    )

    print("Seeding Scenario 02: Flaky Test (High status flips)...")
    b2 = Build(
        pipeline_id=pipeline.id,
        commit_sha="c9d201ab",
        branch="feature/cart-sync",
        build_number=102,
        status=BuildStatus.FAILURE,
        trigger="pull_request",
        started_at=datetime.utcnow() - timedelta(hours=2, minutes=10),
        completed_at=datetime.utcnow() - timedelta(hours=2, minutes=5),
        duration_seconds=310.0
    )
    db.add(b2)
    db.flush()

    tr2 = TestRun(
        build_id=b2.id,
        runner_os="ubuntu-latest",
        runner_version="22.04",
        total_tests=50,
        passed_tests=49,
        failed_tests=1,
        started_at=datetime.utcnow() - timedelta(hours=2, minutes=9),
        completed_at=datetime.utcnow() - timedelta(hours=2, minutes=5)
    )
    db.add(tr2)
    db.flush()

    test2 = Test(
        repository_id=repo.id,
        name="test_cart_concurrency_race",
        suite_name="services.cart.test_concurrency",
        file_path="tests/test_cart_sync.py",
        line_number=112,
        flakiness_score=0.72,
        failure_rate=0.45,
        run_count=48
    )
    db.add(test2)
    db.flush()

    fp2 = Fingerprint(
        hash_value="fp_timeout_race_cart_lock",
        error_type="TimeoutException",
        normalized_message="TimeoutException: Lock acquisition timed out after 5000ms in thread sync",
        location="tests/test_cart_sync.py:112",
        occurrence_count=22,
        first_seen_at=datetime.utcnow() - timedelta(days=14),
        last_seen_at=datetime.utcnow() - timedelta(hours=2, minutes=5)
    )
    db.add(fp2)
    db.flush()

    fail2 = Failure(
        test_run_id=tr2.id,
        test_id=test2.id,
        fingerprint_id=fp2.id,
        error_type="TimeoutException",
        raw_message="TimeoutException: Lock acquisition timed out after 5000ms",
        normalized_message="TimeoutException: Lock acquisition timed out after <NUM>ms",
        raw_stack_trace="File \"tests/test_cart_sync.py\", line 112, in test_cart_concurrency_race\nwait.until_condition()",
        normalized_stack_trace="File \"tests/test_cart_sync.py\", line 112, in test_cart_concurrency_race\nwait.until_condition()",
        classification=FailureClassification.FLAKY_TEST,
        classification_confidence=0.92,
        flakiness_score=0.72,
        regression_prob=0.12,
        severity=SeverityLevel.LOW,
        created_at=datetime.utcnow() - timedelta(hours=2, minutes=5)
    )
    db.add(fail2)
    db.flush()

    vector_store.insert_failure_embedding(
        point_id=fail2.id,
        vector=generate_dense_embedding(f"{fail2.error_type} {fail2.normalized_message}"),
        payload={"fingerprint_id": fp2.id, "failure_id": fail2.id, "test_id": test2.id, "classification": fail2.classification.value}
    )

    print("Seeding Scenario 03: Duplicate / Co-occurring Failures...")
    # Two failures with same fingerprint
    b3 = Build(
        pipeline_id=pipeline.id,
        commit_sha="e7192a01",
        branch="main",
        build_number=103,
        status=BuildStatus.FAILURE,
        trigger="push",
        started_at=datetime.utcnow() - timedelta(hours=1, minutes=30),
        completed_at=datetime.utcnow() - timedelta(hours=1, minutes=25),
        duration_seconds=290.0
    )
    db.add(b3)
    db.flush()

    tr3 = TestRun(
        build_id=b3.id,
        runner_os="ubuntu-latest",
        runner_version="22.04",
        total_tests=60,
        passed_tests=58,
        failed_tests=2,
        started_at=datetime.utcnow() - timedelta(hours=1, minutes=29),
        completed_at=datetime.utcnow() - timedelta(hours=1, minutes=25)
    )
    db.add(tr3)
    db.flush()

    fp3 = Fingerprint(
        hash_value="fp_redis_connection_refused_6379",
        error_type="ConnectionRefusedError",
        normalized_message="ConnectionRefusedError: Connection refused to redis-cluster:6379",
        location="backend/services/cache.py:42",
        occurrence_count=5,
        first_seen_at=datetime.utcnow() - timedelta(days=2),
        last_seen_at=datetime.utcnow() - timedelta(hours=1, minutes=25)
    )
    db.add(fp3)
    db.flush()

    fail3_a = Failure(
        test_run_id=tr3.id,
        test_id=test1.id,
        fingerprint_id=fp3.id,
        error_type="ConnectionRefusedError",
        raw_message="ConnectionRefusedError: [Errno 111] Connection refused to redis-cluster:6379",
        normalized_message="ConnectionRefusedError: [Errno <NUM>] Connection refused to redis-cluster:<PORT>",
        raw_stack_trace="File \"backend/services/cache.py\", line 42, in get_redis\nsocket.connect(('redis-cluster', 6379))",
        normalized_stack_trace="File \"backend/services/cache.py\", line 42, in get_redis\nsocket.connect(('redis-cluster', <PORT>))",
        classification=FailureClassification.NETWORK,
        classification_confidence=0.95,
        flakiness_score=0.08,
        regression_prob=0.05,
        severity=SeverityLevel.MEDIUM,
        created_at=datetime.utcnow() - timedelta(hours=1, minutes=25)
    )
    db.add(fail3_a)

    print("Seeding Scenario 04: Infrastructure Runner OOM...")
    fail4 = Failure(
        test_run_id=tr3.id,
        test_id=test2.id,
        fingerprint_id=None,
        error_type="RunnerDiedError",
        raw_message="Process killed by OOMKiller (exit code 137). Memory cgroup limit exceeded on host runner.",
        normalized_message="Process killed by OOMKiller (exit code <NUM>). Memory cgroup limit exceeded on host runner.",
        raw_stack_trace="runner agent terminated abruptly during build stage",
        normalized_stack_trace="runner agent terminated abruptly during build stage",
        classification=FailureClassification.INFRASTRUCTURE,
        classification_confidence=0.98,
        flakiness_score=0.02,
        regression_prob=0.01,
        severity=SeverityLevel.HIGH,
        created_at=datetime.utcnow() - timedelta(hours=1, minutes=10)
    )
    db.add(fail4)

    print("Seeding Scenario 05: External Dependency Outage (503)...")
    fail5 = Failure(
        test_run_id=tr3.id,
        test_id=test1.id,
        fingerprint_id=None,
        error_type="HTTPError",
        raw_message="HTTPError: 503 Service Unavailable connecting to https://api.stripe.com/v1/tokens",
        normalized_message="HTTPError: 503 Service Unavailable connecting to <URL>",
        raw_stack_trace="File \"services/payment.py\", line 75, in call_stripe\nres.raise_for_status()",
        normalized_stack_trace="File \"services/payment.py\", line 75, in call_stripe\nres.raise_for_status()",
        classification=FailureClassification.DEPENDENCY,
        classification_confidence=0.94,
        flakiness_score=0.03,
        regression_prob=0.02,
        severity=SeverityLevel.MEDIUM,
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.add(fail5)

    print("Seeding Scenario 06: Build Toolchain Failure...")
    fail6 = Failure(
        test_run_id=tr3.id,
        test_id=test1.id,
        fingerprint_id=None,
        error_type="BuildFailure",
        raw_message="TypeScript compilation error: Cannot find module '@company/core-types'",
        normalized_message="TypeScript compilation error: Cannot find module '<PKG>'",
        raw_stack_trace="tsc --noEmit failed with exit code 1",
        normalized_stack_trace="tsc --noEmit failed with exit code 1",
        classification=FailureClassification.BUILD_FAILURE,
        classification_confidence=0.99,
        flakiness_score=0.01,
        regression_prob=0.85,
        severity=SeverityLevel.HIGH,
        created_at=datetime.utcnow() - timedelta(minutes=45)
    )
    db.add(fail6)

    print("Seeding Scenario 07: Successful Rerun...")
    b7 = Build(
        pipeline_id=pipeline.id,
        commit_sha=c1.sha,
        branch="main",
        build_number=105,
        status=BuildStatus.SUCCESS,
        trigger="workflow_dispatch",
        started_at=datetime.utcnow() - timedelta(minutes=15),
        completed_at=datetime.utcnow() - timedelta(minutes=10),
        duration_seconds=285.0
    )
    db.add(b7)
    db.flush()

    tr7 = TestRun(
        build_id=b7.id,
        runner_os="ubuntu-latest",
        runner_version="22.04",
        total_tests=60,
        passed_tests=60,
        failed_tests=0,
        started_at=datetime.utcnow() - timedelta(minutes=14),
        completed_at=datetime.utcnow() - timedelta(minutes=10)
    )
    db.add(tr7)

    db.commit()
    print("Demo scenarios seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed_all()
