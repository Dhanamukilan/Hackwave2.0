import logging
import jwt
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.core.database import init_db, SessionLocal
from backend.app.core.security import hash_password, verify_password
from backend.app.models.auth import User
from backend.app.models.base import UserRole
from backend.app.middleware.audit_logger import AuditLogMiddleware
from backend.app.middleware.rate_limiter import rate_limiter

# Routers
from backend.app.api.auth import router as auth_router
from backend.app.api.pipelines import router as pipelines_router
from backend.app.api.failures import router as failures_router
from backend.app.api.investigations import router as investigations_router
from backend.app.api.ml import router as ml_router
from backend.app.api.webhooks import router as webhooks_router
from backend.app.api.audit import router as audit_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_default_admin():
    import secrets
    db = SessionLocal()
    try:
        admin = db.query(User).filter((User.username == "admin") | (User.email == "admin@example.com")).first()

        is_legacy_compromised = False
        if admin and admin.hashed_password:
            try:
                if verify_password("AdminPass123!", admin.hashed_password):
                    is_legacy_compromised = True
                    logger.warning("Detected insecure legacy admin password! Forcing immediate credential reset.")
            except Exception:
                pass

        if not admin or is_legacy_compromised:
            bootstrap_pw = settings.ADMIN_BOOTSTRAP_PASSWORD
            generated = False

            if not bootstrap_pw:
                if settings.ENV.lower() in ["production", "prod", "staging"]:
                    raise RuntimeError(
                        "CRITICAL SECURITY CONFIGURATION ERROR: ADMIN_BOOTSTRAP_PASSWORD must be configured "
                        "in production/staging environments. Startup aborted."
                    )
                bootstrap_pw = secrets.token_urlsafe(16)
                generated = True

            hashed = hash_password(bootstrap_pw)

            if not admin:
                admin = User(
                    username="admin",
                    email="admin@example.com",
                    hashed_password=hashed,
                    role=UserRole.ADMIN,
                    is_active=True,
                    must_change_password=True
                )
                db.add(admin)
            else:
                admin.hashed_password = hashed
                admin.must_change_password = True
                admin.is_active = True

            db.commit()

            if generated:
                banner = (
                    "\n" + "=" * 80 + "\n"
                    + "[SECURITY NOTICE] INITIAL BOOTSTRAP ADMINISTRATOR ACCOUNT CREATED\n"
                    + "-" * 80 + "\n"
                    + "  Username: admin\n"
                    + f"  Password: {bootstrap_pw}\n"
                    + "-" * 80 + "\n"
                    + "  SAVE THIS NOW — shown once on initial bootstrap!\n"
                    + "  Password is not stored in plaintext anywhere (only bcrypt hash is persisted).\n"
                    + "  You MUST change this password upon first login.\n"
                    + "=" * 80 + "\n"
                )
                print(banner, flush=True)
                logger.info("Generated cryptographically random bootstrap admin password and printed one-time notice.")
            else:
                logger.info("Bootstrap administrator account initialized from ADMIN_BOOTSTRAP_PASSWORD. Password change required on first login.")
        else:
            logger.info("Admin account verified in database. Existing credentials preserved.")
    except Exception as e:
        logger.error(f"Error seeding default admin: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas and default configuration...")
    init_db()
    seed_default_admin()
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic CI/CD Failure Triage, Root Cause Analysis, and Flaky-Test Intelligence Platform",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit Log Middleware
app.add_middleware(AuditLogMiddleware)

# Rate Limiter Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Don't rate limit health checks
        if not request.url.path.endswith("/health"):
            rate_limiter.check_rate_limit(request)
        return await call_next(request)

app.add_middleware(RateLimitMiddleware)

# Forced Password Change Middleware
class ForcePasswordChangeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            path = request.url.path
            allowed_paths = [
                f"{settings.API_V1_PREFIX}/auth/change-password",
                f"{settings.API_V1_PREFIX}/auth/me",
                f"{settings.API_V1_PREFIX}/auth/login",
            ]
            if path not in allowed_paths and path.startswith(settings.API_V1_PREFIX):
                try:
                    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
                    username = payload.get("sub")
                    if username:
                        db = SessionLocal()
                        try:
                            user = db.query(User).filter_by(username=username).first()
                            if user and user.must_change_password:
                                return JSONResponse(
                                    status_code=403,
                                    content={"detail": "Password change required before accessing other endpoints"}
                                )
                        finally:
                            db.close()
                except Exception:
                    pass
        return await call_next(request)

app.add_middleware(ForcePasswordChangeMiddleware)

# Include Routers under API_V1_PREFIX
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(pipelines_router, prefix=settings.API_V1_PREFIX)
app.include_router(failures_router, prefix=settings.API_V1_PREFIX)
app.include_router(investigations_router, prefix=settings.API_V1_PREFIX)
app.include_router(ml_router, prefix=settings.API_V1_PREFIX)
app.include_router(webhooks_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)

@app.get("/", tags=["Root"])
def root_info():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "webhook_endpoint": f"{settings.API_V1_PREFIX}/webhooks/github",
        "docs_url": "/docs",
        "ui_dashboard_url": "http://localhost:5173"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
    }

