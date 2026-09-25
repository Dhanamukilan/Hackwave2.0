"""
Scenario 04: Infrastructure Runner Outage
Analyzes runner crash due to host memory cgroup exhaustion (OOMKiller).
Classifies as INFRASTRUCTURE, sets High severity, and attributes cause to host limits.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Failure, FailureClassification

def run():
    db = SessionLocal()
    f = db.query(Failure).filter_by(classification=FailureClassification.INFRASTRUCTURE).first()
    if not f:
        print("No infrastructure failure found.")
        return

    print(f"[Scenario 04] Infrastructure Failure ID: {f.id}")
    print(f"Error Type: {f.error_type}")
    print(f"Classification: {f.classification.value}")
    print(f"Confidence: {f.classification_confidence}")
    print(f"Severity: {f.severity.value}")
    print(f"Normalized Message: {f.normalized_message}")

    db.close()

if __name__ == "__main__":
    run()
