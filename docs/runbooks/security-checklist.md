# AG004 Security Audit & Compliance Checklist

Per Section 14 of `projectdocs/project-solution-detailes.md` (Authentication, Secrets, Input Validation, Audit Logging, Rate Limiting, and Human Approval Gates).

This checklist confirms actual code-level implementation, citing the exact files and lines where each security control is enforced.

---

## 1. Authentication & Session Management (JWT)
- **Status:** Verified & Enforced
- **Implementation File:** [`backend/app/core/security.py`](file:///C:/projects/Hackwave2.0/backend/app/core/security.py)
  - `create_access_token` (Lines 30–36): Generates signed JWT tokens with configured expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`) using HMAC-SHA256 (`settings.JWT_ALGORITHM`) and `settings.JWT_SECRET`.
  - `get_current_user` (Lines 38–70): Decodes and validates bearer tokens, extracts the `sub` claim, and resolves the user against the database.
  - `oauth2_scheme` (Line 18): OAuth2 Password Bearer scheme bound to `/api/v1/auth/login`.
- **Endpoints:** [`backend/app/api/auth.py`](file:///C:/projects/Hackwave2.0/backend/app/api/auth.py#L47-L66) (`POST /api/v1/auth/login`).

---

## 2. Role-Based Access Control (RBAC)
- **Status:** Verified & Enforced
- **Implementation File:** [`backend/app/core/security.py`](file:///C:/projects/Hackwave2.0/backend/app/core/security.py)
  - `require_roles(allowed_roles)` (Lines 72–80): Dependency factory validating that `current_user.role` matches authorized permissions, returning `HTTP 403 Forbidden` on role violations.
- **Enforced Protected Endpoints:**
  - `POST /api/v1/investigations/{id}/remediations/{id}/approve`: Restricted to `[ADMIN, INVESTIGATOR]` ([`backend/app/api/investigations.py#L40`](file:///C:/projects/Hackwave2.0/backend/app/api/investigations.py#L40)).
  - `GET /api/v1/audit/logs`: Restricted to `[ADMIN, INVESTIGATOR]` ([`backend/app/api/audit.py#L19`](file:///C:/projects/Hackwave2.0/backend/app/api/audit.py#L19)).
  - `GET /api/v1/auth/users`: Restricted to `[ADMIN]` ([`backend/app/api/auth.py#L99`](file:///C:/projects/Hackwave2.0/backend/app/api/auth.py#L99)).
  - `POST /api/v1/failures/{id}/investigate`: Requires authenticated user ([`backend/app/api/failures.py#L55`](file:///C:/projects/Hackwave2.0/backend/app/api/failures.py#L55)).

---

## 3. GitHub Webhook HMAC Signature Verification
- **Status:** Verified & Enforced
- **Implementation File:** [`ingestion/webhook_handlers/github_webhook.py`](file:///C:/projects/Hackwave2.0/ingestion/webhook_handlers/github_webhook.py)
  - `verify_github_signature` (Lines 10–33): Computes SHA-256 HMAC digest of incoming raw payload bytes and performs constant-time comparison via `hmac.compare_digest(f"sha256={computed_hash}", signature_header)`.
- **Endpoint Enforcement:** [`backend/app/api/webhooks.py`](file:///C:/projects/Hackwave2.0/backend/app/api/webhooks.py#L23-L30)
  - Inspects `x_hub_signature_256` header on incoming POST requests against `settings.GITHUB_WEBHOOK_SECRET`. Rejects invalid payloads with `HTTP 401 Unauthorized`.

---

## 4. Pydantic Input Validation on All API Request Bodies
- **Status:** Verified & Enforced
- **Implementation Files:**
  - [`backend/app/schemas/auth.py`](file:///C:/projects/Hackwave2.0/backend/app/schemas/auth.py):
    - `UserRegister` (Lines 6–10): Enforces username string, RFC-compliant email formatting via `EmailStr`, password string, and optional `UserRole`.
    - `UserLogin` (Lines 12–14): Validates login payload types.
    - `PasswordChangeRequest` (Lines 29–31): Validates `old_password` and `new_password` inputs.
  - [`backend/app/schemas/failure.py`](file:///C:/projects/Hackwave2.0/backend/app/schemas/failure.py):
    - `IngestExecutionRequest` (Lines 39–48): Validates repository, pipeline, commit SHA, branch name, and test run metadata.
  - [`backend/app/schemas/investigation.py`](file:///C:/projects/Hackwave2.0/backend/app/schemas/investigation.py):
    - `FeedbackCreate` (Lines 37–41): Validates investigation UUID, boolean flags, and classification values.
  - [`backend/app/api/ml.py`](file:///C:/projects/Hackwave2.0/backend/app/api/ml.py):
    - `ClassifyRequest` (Lines 13–23) and `FlakyPredictRequest` (Lines 24–27): Validates numeric bounds, duration floats, and run history payloads.

---

## 5. Log Sanitization in Ingestion Pipeline
- **Status:** Verified & Enforced
- **Implementation File:** [`ingestion/log_normalizer/normalizer.py`](file:///C:/projects/Hackwave2.0/ingestion/log_normalizer/normalizer.py)
  - `SECRET_TOKEN_PATTERNS` (Lines 17–34): Regex pattern bank identifying API keys, bearer tokens, passwords, AWS access keys, GitHub tokens, and private secrets.
  - `sanitize_secrets` (Lines 36–43): Replaces all sensitive matches with `[REDACTED_SECRET]`.
  - Enforced in normalization pipeline at Lines 53 and 81 prior to database storage or vector embedding generation.

---

## 6. Audit Logging of Sensitive & Mutation Actions
- **Status:** Verified & Enforced
- **Implementation Files:**
  - [`backend/app/middleware/audit_logger.py`](file:///C:/projects/Hackwave2.0/backend/app/middleware/audit_logger.py):
    - `AuditLogMiddleware` (Lines 11–41): Asynchronous middleware intercepting all HTTP state modifications (`POST`, `PUT`, `DELETE`, `PATCH`). Records client IP, path, status code, and actor details into the `audit_logs` table.
  - [`backend/app/api/investigations.py`](file:///C:/projects/Hackwave2.0/backend/app/api/investigations.py#L47):
    - Explicit audit capture during remediation approvals (`approve_and_execute`).
  - [`backend/app/api/audit.py`](file:///C:/projects/Hackwave2.0/backend/app/api/audit.py#L15-L26):
    - Secured endpoint (`GET /api/v1/audit/logs`) exposing audit records to compliance officers and administrators.

---

## 7. Rate Limiting on Public & Webhook Endpoints
- **Status:** Verified & Enforced
- **Implementation Files:**
  - [`backend/app/middleware/rate_limiter.py`](file:///C:/projects/Hackwave2.0/backend/app/middleware/rate_limiter.py):
    - `SlidingWindowRateLimiter` (Lines 7–32): Thread-safe in-memory sliding-window limiter enforcing request quotas per client IP within a 60-second window. Raises `HTTP 429 Too Many Requests`.
  - [`backend/app/main.py`](file:///C:/projects/Hackwave2.0/backend/app/main.py#L128-L135):
    - `RateLimitMiddleware` applied globally across API endpoints.

---

## 8. Agent Tool Allowlist (No Dynamic Registration, No Shell Execution)
- **Status:** Verified & Enforced
- **Implementation File:** [`agents/tools/allowlisted_tools.py`](file:///C:/projects/Hackwave2.0/agents/tools/allowlisted_tools.py)
  - Exactly 11 explicit allowlisted read methods bounded to database queries and vector similarity lookups:
    1. `get_test_history` (Line 19)
    2. `get_failure_history` (Line 42)
    3. `get_flakiness_history` (Line 66)
    4. `get_git_commit` (Line 89)
    5. `get_changed_files` (Line 111)
    6. `get_component_owner` (Line 133)
    7. `get_environment_history` (Line 158)
    8. `get_deployment_history` (Line 183)
    9. `calculate_flakiness` (Line 206)
    10. `search_similar_failures` (Line 223)
    11. `get_runtime_evidence` (Line 238)
  - **Static Boundary Audit:**
    - Zero dynamic tool registration APIs.
    - Zero subprocess, `os.system()`, `Popen`, `eval()`, or `exec()` invocations across the `agents/` directory.

---

## 9. Human Approval Gate on Remediation Actions
- **Status:** Verified & Enforced
- **Implementation File:** [`agents/remediation_agent/remediation_agent.py`](file:///C:/projects/Hackwave2.0/agents/remediation_agent/remediation_agent.py)
  - `propose_remediation` (Lines 53–64): Sets initial status strictly to `RemediationStatus.PENDING_APPROVAL`. Never triggers downstream execution automatically.
  - `approve_and_execute` (Lines 66–115): Enforces human gate; checks that `user_role` is `ADMIN` or `INVESTIGATOR` and that current status is `PENDING_APPROVAL` before transitioning to `APPROVED` / `EXECUTED` and invoking the CI adapter.
- **Integration Test Coverage:** Verified in [`tests/integration/test_api.py`](file:///C:/projects/Hackwave2.0/tests/integration/test_api.py) and [`tests/unit/test_agents.py`](file:///C:/projects/Hackwave2.0/tests/unit/test_agents.py).

---

## 10. Bootstrap Credential Management & Zero Hardcoded Passwords
- **Status:** Verified & Enforced
- **Implementation Files:**
  - [`backend/app/main.py`](file:///C:/projects/Hackwave2.0/backend/app/main.py#L27-L99):
    - `seed_default_admin`: Eliminates static default password. Evaluates `settings.ADMIN_BOOTSTRAP_PASSWORD`. If missing, aborts startup in production/staging or generates a cryptographically random password (`secrets.token_urlsafe(16)`) in local dev, logged once to stdout with a security banner.
    - Automatically detects and invalidates legacy compromised password hashes (`AdminPass123!`).
  - [`backend/app/models/auth.py`](file:///C:/projects/Hackwave2.0/backend/app/models/auth.py#L16):
    - `must_change_password` flag initialized to `True` for bootstrap accounts.
  - [`backend/app/main.py`](file:///C:/projects/Hackwave2.0/backend/app/main.py#L137-L170):
    - `ForcePasswordChangeMiddleware`: Blocks all non-auth endpoints with `HTTP 403 Forbidden` until password rotation is completed via `POST /api/v1/auth/change-password`.
