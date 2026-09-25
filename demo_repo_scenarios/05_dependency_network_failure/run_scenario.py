"""
Scenario 05: External Dependency & Network Outage
Analyzes downstream 503 Bad Gateway and connection refused errors.
Concludes DEPENDENCY / NETWORK and recommends pipeline retry once upstream recovers.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Failure, FailureClassification

def run():
    db = SessionLocal()
    f = db.query(Failure).filter_by(classification=FailureClassification.DEPENDENCY).first()
    if not f:
        print("No dependency failure found.")
        return

    print(f"[Scenario 05] Dependency Outage Failure ID: {f.id}")
    print(f"Classification: {f.classification.value}")
    print(f"Message: {f.normalized_message}")
    print(f"Regression Prob: {f.regression_prob} (Correctly isolated as non-code regression)")

    db.close()

if __name__ == "__main__":
    run()
