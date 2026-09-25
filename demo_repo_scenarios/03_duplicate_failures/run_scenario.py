"""
Scenario 03: Duplicate & Co-occurring Failures
Identifies multiple failures sharing the same canonical error fingerprint
and groups them via semantic vector similarity in Qdrant.
"""
import sys, os
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path: sys.path.insert(0, root_dir)

from backend.app.core.database import SessionLocal
from backend.app.models import Fingerprint, Failure

def run():
    db = SessionLocal()
    fp = db.query(Fingerprint).filter(Fingerprint.occurrence_count > 1).first()
    if not fp:
        print("No duplicate fingerprint found.")
        return

    print(f"[Scenario 03] Canonical Fingerprint: {fp.hash_value}")
    print(f"Error Type: {fp.error_type}")
    print(f"Total Occurrences: {fp.occurrence_count}")
    print(f"First Seen: {fp.first_seen_at}")
    print(f"Last Seen:  {fp.last_seen_at}")

    failures = db.query(Failure).filter_by(fingerprint_id=fp.id).all()
    print(f"\nLinked Failures across test runs ({len(failures)} total):")
    for f in failures:
        print(f" - Failure ID: {f.id} | Severity: {f.severity.value} | Created: {f.created_at}")

    db.close()

if __name__ == "__main__":
    run()
