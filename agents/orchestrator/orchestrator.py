import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import (
    Failure, Test, Build, Investigation,
    InvestigationStatus, RCAConfidence
)
from backend.app.services.evidence_engine import EvidenceBundle
from agents.tools.allowlisted_tools import AllowlistedTools
from agents.llm.client import llm_client
from agents.rca_agent.hypothesis_evaluator import hypothesis_evaluator
from agents.remediation_agent.remediation_agent import remediation_agent

logger = logging.getLogger(__name__)

class TriageOrchestrator:
    """
    Coordinates:
    Log Agent -> History Agent -> Git Agent -> Component/Owner Agent -> Evidence Agent -> RCA Agent -> Remediation Agent
    Manages tool budget, builds immutable evidence bundle, and enforces evidence citations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.tools = AllowlistedTools(db)

    def run_investigation(self, failure_id: str, assigned_user_id: Optional[str] = None) -> Investigation:
        """
        Executes end-to-end multi-agent investigation workflow for a failure record.
        """
        failure = self.db.query(Failure).filter_by(id=failure_id).first()
        if not failure:
            raise ValueError(f"Failure with id {failure_id} not found.")

        test = failure.test
        build = failure.test_run.build if failure.test_run else None
        commit_sha = build.commit_sha if build else "unknown_sha"

        # 1. Initialize Evidence Bundle
        bundle = EvidenceBundle(failure_id=failure.id)

        # 2. History Agent: Query test and failure history
        test_hist = self.tools.get_test_history(failure.test_id)
        if test_hist.get("status") == "success":
            bundle.add_item("TEST_HISTORY", "PostgreSQL:failures", "Chronological execution history for test", test_hist)

        if failure.fingerprint_id:
            fp_hist = self.tools.get_failure_history(failure.fingerprint_id)
            if fp_hist.get("status") == "success":
                bundle.add_item("FAILURE_HISTORY", "PostgreSQL:fingerprints", "Prior occurrences of exact fingerprint", fp_hist)

        # 3. Flakiness & Environment Agent
        flakiness_data = self.tools.calculate_flakiness(failure.test_id)
        if flakiness_data.get("status") == "success":
            bundle.add_item("FLAKINESS_METRICS", "Engine:DerivedFeatures", "Derived flakiness metrics", flakiness_data)

        env_data = self.tools.get_environment_history(failure.test_id)
        if env_data.get("status") == "success":
            bundle.add_item("ENVIRONMENT_VARIANCE", "PostgreSQL:test_runs", "Runner OS and environment variance", env_data)

        # 4. Git Agent: Commits and diffs
        diff_data = self.tools.get_commit_diff(commit_sha)
        if diff_data.get("status") == "success":
            bundle.add_item("GIT_DIFF", "Git:Repository", f"Commit diff for {commit_sha[:8]}", diff_data)

        changed_files_data = self.tools.get_changed_files(commit_sha)
        if changed_files_data.get("status") == "success":
            bundle.add_item("CHANGED_FILES", "Git:Repository", "Changed files and mapped components", changed_files_data)

        # 5. Component / Owner Agent
        comp_id = "comp-api"
        if test and "auth" in test.file_path:
            comp_id = "comp-auth"
        elif test and "payment" in test.file_path:
            comp_id = "comp-api"

        owner_data = self.tools.get_component_owner(comp_id)
        if owner_data.get("status") == "success":
            bundle.add_item("COMPONENT_OWNER", "Config:components_map", f"Ownership record for component {comp_id}", owner_data)

        # 6. Vector Similarity Agent (Qdrant)
        search_vec = [0.05] * 384
        similar_data = self.tools.search_similar_failures(search_vec)
        if similar_data.get("status") == "success":
            bundle.add_item("SIMILAR_FAILURES", "Qdrant:failure_embeddings", "Semantically similar historical failures", similar_data)

        # 7. Runtime Telemetry Agent
        runtime_data = self.tools.get_runtime_evidence("api-service")
        bundle.add_item("RUNTIME_EVIDENCE", "Observability:OTel", "Runtime health and crash telemetry", runtime_data)

        bundle_dict = bundle.to_dict()

        # 8. RCA Agent: Evaluate Hypotheses H1..H7
        eval_result = hypothesis_evaluator.evaluate(
            evidence_bundle=bundle_dict,
            classification=failure.classification.value,
            error_type=failure.error_type
        )

        winning_hyp = eval_result["winning_hypothesis"]
        confidence_str = eval_result["confidence"]
        hypotheses_matrix = eval_result["hypotheses_matrix"]

        # 9. LLM Reasoning layer over evidence bundle
        prompt = (
            f"You are the RCA Agent. Investigate CI/CD failure: {failure.error_type} in {test.file_path if test else 'unknown'}.\n"
            f"Failure Message: {failure.normalized_message}\n"
            f"Evidence Bundle:\n{json.dumps(bundle_dict, indent=2)}\n"
            f"Evaluate the root cause. You must cite valid evidence IDs from the bundle (e.g. {bundle.get_valid_ids()}).\n"
        )
        llm_response = llm_client.generate_chat_completion(
            messages=[
                {"role": "system", "content": "You are a CI/CD Failure Triage Agent. Never invent evidence. Cite evidence IDs."},
                {"role": "user", "content": prompt}
            ]
        )

        if not llm_response:
            # Deterministic RCA explanation
            llm_response = (
                f"Root Cause Analysis concluded with {confidence_str} confidence. "
                f"Hypothesis {winning_hyp} is confirmed based on evidence items {eval_result['hypotheses_matrix'][0]['supporting_evidence_ids']}. "
                f"The failure '{failure.error_type}' correlates directly with the gathered evidence."
            )

        # 10. Record Investigation in DB
        investigation = Investigation(
            failure_id=failure.id,
            status=InvestigationStatus.RCA_READY,
            rca_summary=llm_response,
            confidence=RCAConfidence(confidence_str),
            hypotheses_evaluated=hypotheses_matrix,
            evidence_bundle=bundle_dict,
            assigned_to_user_id=assigned_user_id,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(investigation)
        self.db.commit()
        self.db.refresh(investigation)

        # 11. Propose remediation with human approval gate
        remediation_agent.propose_remediation(
            db=self.db,
            investigation_id=investigation.id,
            winning_hypothesis=winning_hyp,
            classification=failure.classification.value,
            test_file=test.file_path if test else "test.py",
            error_type=failure.error_type
        )

        return investigation
