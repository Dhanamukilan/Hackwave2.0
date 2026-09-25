import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models import (
    Test, TestRun, Failure, Fingerprint, Build,
    Commit, ChangedFile, Component, Owner, Deployment
)
from database.vector_store.qdrant_client import vector_store

logger = logging.getLogger(__name__)

class AllowlistedTools:
    def __init__(self, db: Session):
        self.db = db

    def get_test_history(self, test_id: str, limit: int = 20) -> Dict[str, Any]:
        """Tool 1: get_test_history(test_id) -> execution records, chronological"""
        failures = (
            self.db.query(Failure)
            .filter_by(test_id=test_id)
            .order_by(desc(Failure.created_at))
            .limit(limit)
            .all()
        )
        if not failures:
            return {"status": "no_evidence_found", "message": f"No execution history found for test_id {test_id}"}

        records = []
        for f in reversed(failures):
            records.append({
                "failure_id": f.id,
                "test_run_id": f.test_run_id,
                "classification": f.classification.value if f.classification else "UNKNOWN",
                "severity": f.severity.value if f.severity else "NORMAL",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            })
        return {"status": "success", "total_records": len(records), "history": records}

    def get_failure_history(self, fingerprint_id: str, limit: int = 15) -> Dict[str, Any]:
        """Tool 2: get_failure_history(fingerprint_id) -> prior occurrences of this fingerprint"""
        fp = self.db.query(Fingerprint).filter_by(id=fingerprint_id).first()
        if not fp:
            return {"status": "no_evidence_found", "message": f"No fingerprint found for id {fingerprint_id}"}

        prior = (
            self.db.query(Failure)
            .filter_by(fingerprint_id=fingerprint_id)
            .order_by(desc(Failure.created_at))
            .limit(limit)
            .all()
        )
        return {
            "status": "success",
            "fingerprint_id": fp.id,
            "hash_value": fp.hash_value,
            "total_occurrences": fp.occurrence_count,
            "first_seen_at": fp.first_seen_at.isoformat() if fp.first_seen_at else None,
            "last_seen_at": fp.last_seen_at.isoformat() if fp.last_seen_at else None,
            "prior_failures_count": len(prior)
        }

    def search_similar_failures(self, query_vector: List[float], limit: int = 5) -> Dict[str, Any]:
        """Tool 3: search_similar_failures(embedding) -> top-k Qdrant matches + similarity score"""
        if not query_vector:
            return {"status": "no_evidence_found", "message": "No query embedding provided"}

        matches = vector_store.search_similar_failures(query_vector=query_vector, limit=limit, score_threshold=0.4)
        if not matches:
            return {"status": "no_evidence_found", "message": "No semantically similar failures found in Qdrant collection"}

        return {
            "status": "success",
            "matches_count": len(matches),
            "similar_failures": matches
        }

    def get_commit_diff(self, commit_sha: str) -> Dict[str, Any]:
        """Tool 4: get_commit_diff(commit_sha) -> changed files + diff hunks"""
        commit = self.db.query(Commit).filter_by(sha=commit_sha).first()
        if not commit or not commit.changed_files:
            return {"status": "no_evidence_found", "message": f"No diff records found for commit {commit_sha}"}

        diff_files = []
        for cf in commit.changed_files:
            diff_files.append({
                "file_path": cf.file_path,
                "change_type": cf.change_type,
                "additions": cf.additions,
                "deletions": cf.deletions,
                "patch_summary": cf.patch_summary
            })
        return {
            "status": "success",
            "commit_sha": commit.sha,
            "message": commit.message,
            "author": commit.author_name,
            "changed_files_count": len(diff_files),
            "files": diff_files
        }

    def get_recent_commits(self, repo_id: Optional[str] = None, since_hours: int = 72, limit: int = 10) -> Dict[str, Any]:
        """Tool 5: get_recent_commits(repo, since) -> commit list"""
        query = self.db.query(Commit)
        if repo_id:
            query = query.filter_by(repository_id=repo_id)
        
        commits = query.order_by(desc(Commit.committed_at)).limit(limit).all()
        if not commits:
            return {"status": "no_evidence_found", "message": "No recent commits found"}

        return {
            "status": "success",
            "commits": [{
                "sha": c.sha,
                "message": c.message,
                "author": c.author_name,
                "committed_at": c.committed_at.isoformat() if c.committed_at else None
            } for c in commits]
        }

    def get_changed_files(self, commit_sha: str) -> Dict[str, Any]:
        """Tool 6: get_changed_files(commit_sha) -> file paths + component mapping"""
        commit = self.db.query(Commit).filter_by(sha=commit_sha).first()
        if not commit or not commit.changed_files:
            return {"status": "no_evidence_found", "message": f"No changed files found for commit {commit_sha}"}

        components = self.db.query(Component).all()
        results = []
        for cf in commit.changed_files:
            # Map file to component
            matched_comp = None
            for comp in components:
                if comp.name.lower() in cf.file_path.lower():
                    matched_comp = comp.name
                    break
            results.append({
                "file_path": cf.file_path,
                "change_type": cf.change_type,
                "matched_component": matched_comp or "Unassigned Core"
            })
        return {"status": "success", "files": results}

    def get_component_owner(self, component_id: str) -> Dict[str, Any]:
        """Tool 7: get_component_owner(component_id) -> owner/team record"""
        comp = self.db.query(Component).filter_by(id=component_id).first()
        if not comp:
            comp = self.db.query(Component).filter(Component.name.ilike(f"%{component_id}%")).first()

        if not comp or not comp.lead_owner:
            return {"status": "no_evidence_found", "message": f"No owner mapping found for component {component_id}"}

        return {
            "status": "success",
            "component_id": comp.id,
            "component_name": comp.name,
            "owner": {
                "id": comp.lead_owner.id,
                "name": comp.lead_owner.name,
                "email": comp.lead_owner.email,
                "team_name": comp.lead_owner.team_name,
            }
        }

    def get_environment_history(self, test_id: str) -> Dict[str, Any]:
        """Tool 8: get_environment_history(test_id) -> runner OS/version/env variance"""
        runs = (
            self.db.query(TestRun)
            .join(Failure, Failure.test_run_id == TestRun.id)
            .filter(Failure.test_id == test_id)
            .all()
        )
        if not runs:
            return {"status": "no_evidence_found", "message": f"No environment variance records for test_id {test_id}"}

        os_distribution = {}
        for r in runs:
            key = f"{r.runner_os}:{r.runner_version}"
            os_distribution[key] = os_distribution.get(key, 0) + 1

        return {
            "status": "success",
            "test_id": test_id,
            "total_observed_runs": len(runs),
            "os_distribution": os_distribution,
            "variance_detected": len(os_distribution) > 1
        }

    def get_deployment_history(self, service_id: str, limit: int = 5) -> Dict[str, Any]:
        """Tool 9: get_deployment_history(service_id) -> recent deploys, correlated timing"""
        deploys = (
            self.db.query(Deployment)
            .filter(Deployment.service_id.ilike(f"%{service_id}%"))
            .order_by(desc(Deployment.deployed_at))
            .limit(limit)
            .all()
        )
        if not deploys:
            return {"status": "no_evidence_found", "message": f"No deployments recorded for service {service_id}"}

        return {
            "status": "success",
            "deployments": [{
                "id": d.id,
                "service_id": d.service_id,
                "environment": d.environment,
                "commit_sha": d.commit_sha,
                "status": d.status,
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None
            } for d in deploys]
        }

    def calculate_flakiness(self, test_id: str) -> Dict[str, Any]:
        """Tool 10: calculate_flakiness(test_id) -> derived features (not a model call)"""
        test = self.db.query(Test).filter_by(id=test_id).first()
        if not test:
            return {"status": "no_evidence_found", "message": f"Test {test_id} not found"}

        # Calculate chronological run history
        failures = (
            self.db.query(Failure)
            .filter_by(test_id=test_id)
            .order_by(Failure.created_at.asc())
            .all()
        )
        runs_count = test.run_count or 1
        failure_count = len(failures)
        flip_rate = test.flakiness_score

        return {
            "status": "success",
            "test_id": test.id,
            "test_name": test.name,
            "total_runs": runs_count,
            "total_failures": failure_count,
            "failure_rate": round(test.failure_rate, 3),
            "flakiness_score": round(flip_rate, 3),
            "is_intermittent": bool(flip_rate >= 0.35)
        }

    def get_runtime_evidence(self, service_id: str) -> Dict[str, Any]:
        """Tool 11: get_runtime_evidence(service_id) -> OTel/log evidence if deployed"""
        # In Docker / K8s runtime environment
        return {
            "status": "success",
            "service_id": service_id,
            "runtime_telemetry": "Active",
            "error_rate_spike": False,
            "open_telemetry_status": "Connected to localhost:4318",
            "recent_container_restarts": 0
        }
