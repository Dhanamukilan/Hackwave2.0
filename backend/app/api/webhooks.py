import logging
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from ingestion.webhook_handlers.github_webhook import verify_github_signature, parse_webhook_event
from ingestion.github_actions_adapter.adapter import github_actions_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header("push"),
    db: Session = Depends(get_db)
):
    payload_bytes = await request.body()

    # 1. Verify HMAC signature if webhook secret configured
    if settings.GITHUB_WEBHOOK_SECRET and settings.GITHUB_WEBHOOK_SECRET != "optional":
        if not verify_github_signature(payload_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook HMAC-SHA256 signature"
            )

    # 2. Parse JSON payload safely
    try:
        payload_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_data = parse_webhook_event(x_github_event, payload_json)
    logger.info(f"Received GitHub webhook event: {x_github_event} for {event_data.get('repository')}")

    ingest_details = None

    # 3. Process workflow_run completion
    if x_github_event == "workflow_run":
        wf_run = payload_json.get("workflow_run", {})
        run_status = wf_run.get("status")
        run_id = str(wf_run.get("id"))
        commit_sha = wf_run.get("head_sha")
        branch = wf_run.get("head_branch")
        repo_name = payload_json.get("repository", {}).get("name", settings.GITHUB_REPO_NAME)
        wf_name = wf_run.get("name", "CI")

        if run_status == "completed":
            logger.info(f"Triggering ingestion for completed workflow run {run_id} ({wf_name}) on commit {commit_sha}")
            ingest_details = github_actions_adapter.ingest_workflow_run(
                db=db,
                run_id=run_id,
                commit_sha=commit_sha,
                branch=branch,
                repo_name=repo_name,
                workflow_name=wf_name
            )

    # 4. Process check_run completion
    elif x_github_event == "check_run":
        check = payload_json.get("check_run", {})
        if check.get("status") == "completed":
            run_id = str(check.get("id"))
            commit_sha = check.get("head_sha")
            repo_name = payload_json.get("repository", {}).get("name", settings.GITHUB_REPO_NAME)
            ingest_details = github_actions_adapter.ingest_workflow_run(
                db=db,
                run_id=run_id,
                commit_sha=commit_sha,
                repo_name=repo_name,
                workflow_name=check.get("name", "Check")
            )

    return {
        "status": "success",
        "event": x_github_event,
        "handled": event_data["handled"],
        "metadata": event_data,
        "ingest_details": ingest_details
    }
