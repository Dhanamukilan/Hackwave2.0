import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Tuple
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

def verify_github_signature(payload_bytes: bytes, signature_header: str, secret: str = None) -> bool:
    """
    Verifies GitHub webhook HMAC-SHA256 signature in constant time.
    """
    secret_key = (secret or settings.GITHUB_WEBHOOK_SECRET).encode("utf-8")
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header")
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        logger.warning("Signature header does not start with sha256=")
        return False

    expected_hash = signature_header[len(prefix):]
    mac = hmac.new(secret_key, msg=payload_bytes, digestmod=hashlib.sha256)
    computed_hash = mac.hexdigest()

    return hmac.compare_digest(computed_hash, expected_hash)

def parse_webhook_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts relevant build/commit/run metadata from GitHub webhook payload.
    """
    result = {
        "event_type": event_type,
        "handled": True,
        "repository": payload.get("repository", {}).get("full_name", "unknown/repo"),
        "commit_sha": None,
        "branch": None,
        "run_id": None,
        "status": None,
        "conclusion": None,
    }

    if event_type == "workflow_run":
        wf_run = payload.get("workflow_run", {})
        result["run_id"] = str(wf_run.get("id"))
        result["commit_sha"] = wf_run.get("head_sha")
        result["branch"] = wf_run.get("head_branch")
        result["status"] = wf_run.get("status")
        result["conclusion"] = wf_run.get("conclusion")
        result["workflow_name"] = wf_run.get("name")
        result["event"] = wf_run.get("event")

    elif event_type == "check_run":
        check = payload.get("check_run", {})
        result["run_id"] = str(check.get("id"))
        result["commit_sha"] = check.get("head_sha")
        result["status"] = check.get("status")
        result["conclusion"] = check.get("conclusion")

    elif event_type == "push":
        result["commit_sha"] = payload.get("after")
        ref = payload.get("ref", "")
        result["branch"] = ref.split("/")[-1] if ref else "main"
        result["commits_count"] = len(payload.get("commits", []))

    elif event_type == "pull_request":
        pr = payload.get("pull_request", {})
        result["commit_sha"] = pr.get("head", {}).get("sha")
        result["branch"] = pr.get("head", {}).get("ref")
        result["action"] = payload.get("action")

    else:
        result["handled"] = False
        logger.info(f"Unhandled GitHub event type: {event_type}")

    return result
