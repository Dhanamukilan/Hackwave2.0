import logging
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from ingestion.webhook_handlers.github_webhook import verify_github_signature, parse_webhook_event
from backend.app.models import Build, Pipeline, Repository, BuildStatus

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

    # Verify HMAC signature if configured
    if settings.GITHUB_WEBHOOK_SECRET and settings.GITHUB_WEBHOOK_SECRET != "optional":
        if not verify_github_signature(payload_bytes, x_hub_signature_256, settings.GITHUB_WEBHOOK_SECRET):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid GitHub webhook HMAC-SHA256 signature"
            )

    try:
        payload_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_data = parse_webhook_event(x_github_event, payload_json)
    logger.info(f"Received GitHub webhook event: {x_github_event} for {event_data.get('repository')}")

    return {
        "status": "received",
        "event": x_github_event,
        "handled": event_data["handled"],
        "metadata": event_data
    }
