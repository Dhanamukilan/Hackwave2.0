"""
Scenario 07: Successful Rerun & Closed Loop
Demonstrates the resolution loop: after the developer approved remediation
(or pushed the code fix), build #105 re-runs and completes with SUCCESS.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Build, BuildStatus

def run():
    db = SessionLocal()
    b = db.query(Build).filter_by(status=BuildStatus.SUCCESS).order_by(Build.build_number.desc()).first()
    if not b:
        print("No successful build found.")
        return

    print(f"[Scenario 07] Verified Closed-Loop Rerun:")
    print(f"Build Number: #{b.build_number}")
    print(f"Commit: {b.commit_sha}")
    print(f"Trigger: {b.trigger}")
    print(f"Status: {b.status.value}")
    print(f"Duration: {b.duration_seconds}s")
    if b.test_runs:
        tr = b.test_runs[0]
        print(f"Tests Passed: {tr.passed_tests} / {tr.total_tests}")
        print(f"Tests Failed: {tr.failed_tests}")

    db.close()

if __name__ == "__main__":
    run()
