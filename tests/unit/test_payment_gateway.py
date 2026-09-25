"""
Live Integration Demonstration: Payment Gateway Regression Test.
Simulates a real product regression where an unhandled gateway timeout returns HTTP 500
instead of the expected HTTP 200, used for verifying end-to-end CI triage & RCA diagnosis.
"""
import pytest

def test_payment_gateway_charge_authorization():
    # Simulated product regression in payment gateway authorization flow
    # Commit introduces timeout exception handling defect
    expected_status_code = 200
    actual_status_code = 500  # Regression: Gateway timeout unhandled

    assert actual_status_code == expected_status_code, (
        f"Payment charge authorization failed: Expected HTTP {expected_status_code} "
        f"but received HTTP {actual_status_code} (Gateway Timeout at api.payment.internal:443)"
    )
