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
