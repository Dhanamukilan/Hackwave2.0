"""
Scenario 06: Build & Toolchain Failure
Analyzes build failure occurring prior to test suite execution (e.g. broken TypeScript types).
Concludes BUILD_FAILURE and identifies missing types package in lockfile.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Failure, FailureClassification

def run():
    db = SessionLocal()
    f = db.query(Failure).filter_by(classification=FailureClassification.BUILD_FAILURE).first()
    if not f:
        print("No build failure found.")
        return

    print(f"[Scenario 06] Build Failure ID: {f.id}")
    print(f"Classification: {f.classification.value}")
    print(f"Severity: {f.severity.value}")
    print(f"Error: {f.raw_message}")

    db.close()

if __name__ == "__main__":
    run()
