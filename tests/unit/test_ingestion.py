import pytest
from backend.app.core.database import SessionLocal, init_db
from backend.app.services.ingestion_service import IngestionService
from ingestion.log_normalizer.junit_parser import parse_junit_xml
from ingestion.log_normalizer.normalizer import extract_error_signature, normalize_log_text

def test_normalization_and_sanitization():
    raw_log = (
        "2026-09-24T12:00:00Z [INFO] Auth bearer eyJhbGciOiJIUzI1NiJ9.test and ghp_abc123456789012345678901234567890123\n"
        "Failed at 0x7fff5fbff8a0 with uuid 123e4567-e89b-12d3-a456-426614174000\n"
        "File \"/home/runner/work/app/app/main.py\", line 55\n"
        "AssertionError: Expected 200 got 500"
    )
    sig = extract_error_signature(raw_log)
    assert sig["error_type"] == "AssertionError"
    assert "[REDACTED_SECRET]" in sig["normalized_text"]
    assert "<MEM_ADDR>" in sig["normalized_text"]
    assert "<UUID>" in sig["normalized_text"]
    assert "<TIMESTAMP>" in sig["normalized_text"]
    assert len(sig["fingerprint_hash"]) == 64

def test_ingestion_end_to_end():
    init_db()
    xml_content = """<testsuites>
      <testsuite name="billing" tests="2">
        <testcase classname="test_billing" name="test_invoice_creation" time="0.05"/>
        <testcase classname="test_billing" name="test_stripe_webhook" time="0.10">
          <failure message="ConnectionError: Failed to connect to api.stripe.com:443" type="ConnectionError">
            File "services/billing.py", line 45, in call_stripe
            raise ConnectionError("Failed to connect to api.stripe.com:443")
          </failure>
        </testcase>
      </testsuite>
    </testsuites>"""

    cases = parse_junit_xml(xml_content)
    assert len(cases) == 2
    assert cases[1]["status"] == "FAILED"
    assert cases[1]["error_info"]["error_type"] == "ConnectionError"

    db = SessionLocal()
    service = IngestionService(db)
    res = service.ingest_test_execution_record(
        repo_name="demo-repo",
        pipeline_name="CI Pipeline",
        commit_sha="commit-12345",
        branch="main",
        test_case_records=cases
    )
    assert res["failed_count"] == 1
    assert len(res["failures_created"]) == 1
    db.close()

def test_realistic_github_actions_log_sanitization():
    """
    Verifies that the log normalizer correctly processes a realistic GitHub Actions runner
    console log containing ANSI escape codes, UTC runner timestamps, memory addresses,
    leaked secrets/tokens, and process UUIDs.
    """
    real_gh_actions_log = (
        "2026-09-25T14:15:01.1293841Z ##[section]Starting: Run test suite\n"
        "2026-09-25T14:15:02.0019284Z \x1b[34m============================= test session starts ==============================\x1b[0m\n"
        "2026-09-25T14:15:03.4910291Z platform linux -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0\n"
        "2026-09-25T14:15:04.1102941Z rootdir: /home/runner/work/Hackwave2.0/Hackwave2.0\n"
        "2026-09-25T14:15:05.8920192Z Environment: GITHUB_TOKEN=ghp_aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5\n"
        "2026-09-25T14:15:06.0192831Z AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n"
        "2026-09-25T14:15:07.1928471Z Object reference at 0x7ffd9b8a21f0 initialized with session 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d\n"
        "2026-09-25T14:15:08.5910293Z \x1b[31m_________________________________ test_payment_charge _________________________________\x1b[0m\n"
        "2026-09-25T14:15:09.1029481Z \x1b[31m>       assert response.status_code == 200\x1b[0m\n"
        "2026-09-25T14:15:09.1029591Z \x1b[31mE       AssertionError: Expected 200 got 500: Server Error\x1b[0m\n"
        "2026-09-25T14:15:09.1030101Z tests/test_payment.py:45: AssertionError\n"
        "2026-09-25T14:15:10.0019283Z ##[error]Process completed with exit code 1."
    )

    sig = extract_error_signature(real_gh_actions_log)

    # 1. Error type correctly parsed
    assert sig["error_type"] == "AssertionError"

    # 2. ANSI escape codes stripped
    assert "\x1b[31m" not in sig["normalized_text"]
    assert "\x1b[0m" not in sig["normalized_text"]

    # 3. GitHub Actions runner timestamps converted
    assert "<TIMESTAMP>" in sig["normalized_text"]
    assert "2026-09-25T14:15:01" not in sig["normalized_text"]

    # 4. Leaked credentials and tokens sanitized
    assert "ghp_aB3dE5fG7hI9jK1lM3nO5pQ7rS9tU1vW3xY5" not in sig["normalized_text"]
    assert "[REDACTED_SECRET]" in sig["normalized_text"]

    # 5. Pointer addresses masked
    assert "0x7ffd9b8a21f0" not in sig["normalized_text"]
    assert "<MEM_ADDR>" in sig["normalized_text"]

    # 6. Session UUIDs masked
    assert "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d" not in sig["normalized_text"]
    assert "<UUID>" in sig["normalized_text"]

    # 7. Deterministic SHA-256 fingerprint produced
    assert len(sig["fingerprint_hash"]) == 64

