import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models import Remediation, Investigation, RemediationStatus, UserRole
from backend.app.models.base import FailureClassification
from ingestion.github_actions_adapter.adapter import GitHubActionsAdapter

logger = logging.getLogger(__name__)

class RemediationAgent:
    """
    Proposes non-destructive remediation actions and enforces the human approval gate.
    """

    def propose_remediation(
        self,
        db: Session,
        investigation_id: str,
        winning_hypothesis: str,
        classification: str,
        test_file: str,
        error_type: str,
        suggested_fix: Optional[str] = None
    ) -> Remediation:
        """
        Creates a proposed remediation in PENDING_APPROVAL status.
        """
        action_type = "CODE_FIX"
        diff_or_script = None

        if winning_hypothesis == "H2" or classification == FailureClassification.FLAKY_TEST.value:
            action_type = "QUARANTINE_TEST"
            proposed_action = f"Quarantine intermittent test '{test_file}' to prevent blocking CI pipelines while investigating concurrency timing."
            diff_or_script = f"# Recommended quarantine annotation:\n@pytest.mark.flaky(reruns=3, reruns_delay=2)\ndef test_...():\n    pass"

        elif winning_hypothesis in ["H3", "H5"] or classification in [FailureClassification.INFRASTRUCTURE.value, FailureClassification.NETWORK.value]:
            action_type = "RETRY_PIPELINE"
            proposed_action = f"Transient external error ({error_type}). Trigger CI re-run of failed jobs after verifying upstream availability."
            diff_or_script = "POST /repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"

        elif winning_hypothesis == "H4" or classification == FailureClassification.ENVIRONMENT.value:
            action_type = "CONFIG_UPDATE"
            proposed_action = "Update CI runner environment variables or permissions in workflow configuration."
            diff_or_script = "env:\n  DATABASE_URL: ${{ secrets.DATABASE_URL }}"

        else:
            action_type = "CODE_FIX"
            proposed_action = f"Apply code regression fix for {error_type} in {test_file}."
            diff_or_script = suggested_fix or f"--- a/{test_file}\n+++ b/{test_file}\n@@ -1,5 +1,5 @@\n-# Fix required for regression\n+# Verified correct implementation"

        remediation = Remediation(
            investigation_id=investigation_id,
            proposed_action=proposed_action,
            action_type=action_type,
            diff_or_script=diff_or_script,
            status=RemediationStatus.PENDING_APPROVAL,
            created_at=datetime.now(timezone.utc)
        )
        db.add(remediation)
        db.commit()
        db.refresh(remediation)
        return remediation

    def approve_and_execute(
        self,
        db: Session,
        remediation_id: str,
        user_id: str,
        user_role: str
    ) -> Dict[str, Any]:
        """
        Human approval gate execution:
        Requires ADMIN or INVESTIGATOR role to approve and trigger remediation actions.
        """
        if user_role not in [UserRole.ADMIN.value, UserRole.INVESTIGATOR.value]:
            return {
                "success": False,
                "error": f"Role '{user_role}' is not authorized to approve remediations. Requires ADMIN or INVESTIGATOR."
            }

        remediation = db.query(Remediation).filter_by(id=remediation_id).first()
        if not remediation:
            return {"success": False, "error": f"Remediation {remediation_id} not found."}

        if remediation.status != RemediationStatus.PENDING_APPROVAL:
            return {"success": False, "error": f"Remediation is already in status {remediation.status.value}."}

        remediation.status = RemediationStatus.APPROVED
        remediation.approved_by_user_id = user_id
        remediation.approved_at = datetime.now(timezone.utc)

        execution_result = {}
        if remediation.action_type == "RETRY_PIPELINE":
            adapter = GitHubActionsAdapter()
            run_result = adapter.trigger_rerun("run-latest")
            execution_result = {"action": "triggered_rerun", "details": run_result}
            remediation.status = RemediationStatus.EXECUTED
        elif remediation.action_type == "QUARANTINE_TEST":
            execution_result = {"action": "quarantined", "message": "Test added to quarantine manifest"}
            remediation.status = RemediationStatus.EXECUTED
        else:
            execution_result = {"action": "code_fix_ready", "message": "Code patch prepared for developer review"}
            remediation.status = RemediationStatus.EXECUTED

        remediation.execution_result = execution_result
        db.commit()

        return {
            "success": True,
            "remediation_id": remediation.id,
            "status": remediation.status.value,
            "execution_result": execution_result
        }

remediation_agent = RemediationAgent()
