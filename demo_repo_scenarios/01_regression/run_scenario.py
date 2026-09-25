"""
Scenario 01: Genuine Code Regression
Simulates a developer pushing a commit that introduces a breaking assertion in payment gateway.
Platform analyzes the failure, isolates code change, assigns REGRESSION classification,
and proposes a CODE_FIX remediation.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Failure, FailureClassification
from agents.orchestrator.orchestrator import TriageOrchestrator

def run():
    db = SessionLocal()
    failure = db.query(Failure).filter_by(classification=FailureClassification.REGRESSION).first()
    if not failure:
        print("Error: No regression failure found in database. Run seed script first.")
        return

    print(f"[Scenario 01] Running RCA Orchestrator for Failure ID {failure.id} ({failure.error_type})...")
    orchestrator = TriageOrchestrator(db)
    inv = orchestrator.run_investigation(failure.id)

    print("\n--- RESULTS ---")
    print(f"Investigation Status: {inv.status.value}")
    print(f"Confidence: {inv.confidence.value}")
    print(f"RCA Summary:\n{inv.rca_summary}\n")
    print(f"Proposed Remediations: {len(inv.remediations)}")
    if inv.remediations:
        print(f"Action: {inv.remediations[0].proposed_action}")
        print(f"Status: {inv.remediations[0].status.value} (Waiting for Human Approval)")

    db.close()

if __name__ == "__main__":
    run()
