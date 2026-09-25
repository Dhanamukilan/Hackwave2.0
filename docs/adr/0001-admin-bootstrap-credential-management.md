# ADR 0001: Administrator Bootstrap Credential Management & Zero Hardcoded Secrets

## Status
Accepted

## Date
2026-09-25

## Context
In early prototyping phases, the platform seeded a default administrator user (`admin`) with a hardcoded static password (`AdminPass123!`) on every boot. This approach introduced critical security vulnerabilities:
1. Predictable default credentials violated the core mandate in Section 14 ("Never hardcode secrets; use environment variables; no plaintext credentials").
2. The credential refreshed on every application restart, overwriting administrator password updates.
3. Client-side code and documentation embedded static defaults, exposing attack vectors across test and deployment artifacts.

## Decision
We adopted a **Hybrid Secure Bootstrap Model with Mandatory Forced Password Rotation**:

1. **Environment Configuration Gate (`ADMIN_BOOTSTRAP_PASSWORD`)**:
   - In non-local production and staging environments (`ENV=production`, `ENV=prod`, `ENV=staging`), setting the `ADMIN_BOOTSTRAP_PASSWORD` environment variable is mandatory. The application aborts startup with a `RuntimeError` if this variable is missing.
   - The environment variable is defined in `.env.example` as an unpopulated placeholder (`ADMIN_BOOTSTRAP_PASSWORD=`) and must never be committed.

2. **Cryptographic Random Generation on Local First-Boot**:
   - In local development (`ENV=development`), if no `ADMIN_BOOTSTRAP_PASSWORD` is supplied, the platform automatically generates a 16-byte cryptographically secure random password via `secrets.token_urlsafe(16)`.
   - The temporary password is output once to stdout with a high-visibility terminal banner and warning (`SAVE THIS NOW — shown once on initial bootstrap!`).
   - Plaintext credentials are never written to disk, databases, or log files. Only a salt-hashed bcrypt digest is persisted.
   - Subsequent boots detect the existing administrator account and preserve its credentials without regeneration or overwriting.

3. **Insecure Legacy Credential Purge**:
   - On startup, the seeding subsystem evaluates existing database records. If the legacy compromised hash for `AdminPass123!` is detected, it is immediately invalidated and replaced with a newly generated bootstrap credential.

4. **Mandatory First-Login Password Rotation (`must_change_password`)**:
   - The `users` model and database schema introduce a `must_change_password` boolean attribute, initialized to `True` for bootstrap accounts.
   - Until rotated via `POST /api/v1/auth/change-password`, all non-auth endpoints reject the session with `HTTP 403 Forbidden` (`detail: "Password change required before accessing other endpoints"`).
   - This boundary is enforced both at the dependency layer (`get_current_user`) and via a global Starlette HTTP middleware (`ForcePasswordChangeMiddleware`).

5. **Client UI & Documentation Remediation**:
   - Hardcoded credential defaults and auto-login routines were purged from `frontend/src/App.jsx`.
   - A dedicated blocking modal requires the administrator to establish a permanent password ($\ge 8$ characters) immediately upon authentication.

## Consequences
- **Positive**:
  - Zero hardcoded credentials in codebase, version control, or production artifacts.
  - Predictable, automated local development bootstrapping without compromising production environments.
  - Strict compliance with Section 14 security specifications.
  - Full audit logging of password rotation operations.
- **Negative / Operational Considerations**:
  - Operators must note the generated password on initial local boot or configure `ADMIN_BOOTSTRAP_PASSWORD` in their environment.
