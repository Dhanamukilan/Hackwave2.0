"""
Scenario 02: Flaky Test Identification
Analyzes an intermittent concurrency test with high historical flip rate.
Platform identifies FLAKY_TEST classification and proposes test quarantine.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Failure, FailureClassification
from agents.orchestrator.orchestrator import TriageOrchestrator

def run():
    db = SessionLocal()
    failure = db.query(Failure).filter_by(classification=FailureClassification.FLAKY_TEST).first()
    if not failure:
        print("Error: No flaky failure found in database.")
        return

    print(f"[Scenario 02] Running RCA for Flaky Test ID {failure.id} ({failure.test.name})...")
    orchestrator = TriageOrchestrator(db)
    inv = orchestrator.run_investigation(failure.id)

    print("\n--- RESULTS ---")
    print(f"Flakiness Score: {failure.flakiness_score}")
    print(f"Regression Prob: {failure.regression_prob} (Independent)")
    print(f"Proposed Action Type: {inv.remediations[0].action_type if inv.remediations else 'None'}")
    print(f"Remediation: {inv.remediations[0].proposed_action if inv.remediations else 'None'}")
    db.close()

if __name__ == "__main__":
    run()
