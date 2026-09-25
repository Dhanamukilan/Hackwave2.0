import logging
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.app.core.database import SessionLocal
from backend.app.models.investigation import AuditLog

logger = logging.getLogger(__name__)

class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Audit logging middleware recording mutation actions and state changes.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # Log state modifications (POST, PUT, DELETE, PATCH)
        if request.method in ["POST", "PUT", "DELETE", "PATCH"] and not request.url.path.endswith("/auth/login"):
            client_ip = request.client.host if request.client else "unknown"
            path = request.url.path
            action = f"{request.method} {path}"

            db = SessionLocal()
            try:
                log_entry = AuditLog(
                    action=action,
                    resource_type="API_ENDPOINT",
                    resource_id=path,
                    details={"status_code": response.status_code},
                    ip_address=client_ip,
                    created_at=datetime.now(timezone.utc)
                )
                db.add(log_entry)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to record audit log: {e}")
            finally:
                db.close()

        return response
