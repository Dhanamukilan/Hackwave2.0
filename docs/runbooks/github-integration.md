# GitHub Integration Runbook & Live Verification Guide

## 1. Architectural Overview & Context

The **AG004 Failure Intelligence Platform** integrates natively with GitHub and GitHub Actions to automate failure triage, flaky test detection, and root-cause analysis (RCA).

```
   +-----------------------------------------------------------------------+
   |                       GitHub Repository (Target)                     |
   |                                                                       |
   |  git push / PR  --->  GitHub Actions CI (.github/workflows/ci.yml)    |
   |                               |                                       |
   |                               v (Test Failure / Results)              |
   |                         Uploads Artifact                              |
   |                      (results/junit.xml)                              |
   +-------------------------------+---------------------------------------+
                                   |
                         Webhook Delivery (HMAC Signed)
                         (workflow_run.completed)
                                   |
                                   v
   +-----------------------------------------------------------------------+
   |                    AG004 Backend & Ingestion Engine                   |
   |                                                                       |
   | 1. HMAC Verification (SHA-256): Reject invalid/unsigned (HTTP 401)    |
   | 2. Idempotency Check: Filter duplicate deliveries by (pipeline, sha)  |
   | 3. GitHub REST Adapter (ingestion/github_actions_adapter):            |
   |    - Downloads & parses JUnit XML artifact (in-memory zip)            |
   |    - Falls back to job console logs if artifact missing               |
   |    - Normalizes & sanitizes logs (masks UUIDs, secrets, timestamps)   |
   |    - Fetches commit details & changed files (git diff/patch)          |
   | 4. Database Persistence (PostgreSQL / SQLite fallback):               |
   |    - Build, TestRun, Test, Failure, Fingerprint, Commit, ChangedFile   |
   | 5. Multi-Agent Triage Orchestrator (agents/orchestrator):             |
   |    - Evaluates hypotheses H1-H7 with strict evidence citations         |
   |    - Generates RCA diagnosis & human-approval-gated remediation       |
   +-----------------------------------------------------------------------+
```

---

## 2. Authentication & Credentials Setup

AG004 supports both **GitHub Apps** (recommended for production multi-tenant deployments) and **Fine-Grained Personal Access Tokens (PAT)** (for scoped single-repo or CI pipeline environments).

### Option A: GitHub App Setup (Production Standard)

1. **Create GitHub App**:
   - In GitHub, navigate to **Settings &rarr; Developer Settings &rarr; GitHub Apps &rarr; New GitHub App**.
   - **App Name:** `AG004-Failure-Intelligence`
   - **Homepage URL:** `https://your-domain.com` (or dev URL).
   - **Webhook:** Active. Set Webhook URL to `https://your-domain.com/api/v1/webhooks/github` and define a high-entropy `Webhook Secret`.
2. **Permissions**:
   - **Repository Permissions**:
     - `Actions`: Read-only (access to workflow runs, artifacts, jobs)
     - `Checks`: Read-only (read check runs and suites)
     - `Contents`: Read-only (read commits, file diffs, branches)
     - `Pull requests`: Read & write (post triage summaries and fix PRs)
   - **Subscribe to Events**:
     - `Push`, `Pull request`, `Workflow run`, `Check run`
3. **Private Key Generation**:
   - Generate a private key (`.pem`) and store it securely (e.g., `certs/github_app.pem`).
4. **Environment Configuration (`.env`)**:
   ```bash
   GITHUB_APP_ID=123456
   GITHUB_APP_PRIVATE_KEY_PATH=/path/to/certs/github_app.pem
   GITHUB_WEBHOOK_SECRET=your-secure-webhook-secret-token
   GITHUB_REPO_OWNER=Dhanamukilan
   GITHUB_REPO_NAME=Hackwave2.0
   ```

### Option B: Fine-Grained Personal Access Token (PAT)

1. In GitHub, navigate to **Settings &rarr; Developer Settings &rarr; Personal Access Tokens &rarr; Fine-grained tokens**.
2. **Repository access:** Selected repositories &rarr; `Hackwave2.0`.
3. **Permissions**:
   - `Actions`: Read-only
   - `Contents`: Read-only
   - `Workflows`: Read and write
4. **Environment Configuration (`.env`)**:
   ```bash
   GITHUB_TOKEN=ghp_...
   GITHUB_WEBHOOK_SECRET=ag004-secure-webhook-secret-token-key-2026
   GITHUB_REPO_OWNER=Dhanamukilan
   GITHUB_REPO_NAME=Hackwave2.0
   ```

> [!IMPORTANT]
> The `.env` file is excluded from version control via `.gitignore`. Never commit plaintext tokens or private keys to the repository.

---

## 3. Webhook Registration & HMAC-SHA256 Verification

### Webhook Registration Scripts

Registration scripts are provided for both Bash and PowerShell:

- **Linux / macOS**:
  ```bash
  chmod +x scripts/register_github_webhook.sh
  ./scripts/register_github_webhook.sh
  ```
- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\register_github_webhook.ps1 -WebhookUrl "https://smee.io/gtwttnMBimPx8V9"
  ```

### HMAC Verification Details

The endpoint `POST /api/v1/webhooks/github` computes the HMAC-SHA256 digest of the raw request payload using `GITHUB_WEBHOOK_SECRET`:
- Header checked: `X-Hub-Signature-256: sha256=<hex_digest>`
- Algorithm: Constant-time comparison `hmac.compare_digest` to prevent timing attacks.
- Missing or invalid signatures immediately return `HTTP 401 Unauthorized`.
- Malformed payloads return `HTTP 400 Bad Request`.
- Verification is fully tested in `tests/integration/test_github_webhook.py`.

### Local Development Webhook Forwarding (Dev-Only)

GitHub requires a publicly reachable URL for webhook deliveries. For local development:

1. **Smee.io (Official GitHub Webhook Proxy — Recommended)**:
   - Create a proxy channel at [smee.io](https://smee.io).
   - Register the channel URL as the webhook target (e.g. `https://smee.io/gtwttnMBimPx8V9`).
   - Forward to local backend:
     ```bash
     npm install --global smee-client
     smee --url https://smee.io/gtwttnMBimPx8V9 --target http://localhost:8000/api/v1/webhooks/github
     ```
2. **Cloudflare Tunnels or ngrok**:
   - `ngrok http 8000`
   - Set Webhook URL to `https://<subdomain>.ngrok-free.app/api/v1/webhooks/github`.

---

## 4. GitHub Actions CI Configuration

The repository CI workflow is located at `.github/workflows/ci.yml`.

```yaml
name: CI

on:
  push:
    branches: [ main, "**" ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    name: build-and-test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f backend/requirements.txt ]; then pip install -r backend/requirements.txt; fi
          pip install pytest httpx

      - name: Run test suite with JUnit XML reporting
        run: |
          mkdir -p results
          export PYTHONPATH=.
          python -m pytest tests/unit/ --junitxml=results/junit.xml

      - name: Upload test results artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: results/junit.xml
          retention-days: 14
```

**Key CI Design Elements:**
1. Generates structured `results/junit.xml` capturing test durations, statuses, failure messages, and stack traces.
2. The `Upload test results artifact` step runs with `if: always()`, guaranteeing test outcome availability to the AG004 ingestion adapter even when test assertions fail.

---

## 5. Ingestion Adapter & Multi-Agent Triage Execution

When a `workflow_run` event with action `completed` is received:

1. **Artifact Extraction**:
   - Queries `GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts`.
   - Locates artifact named `test-results`, downloads the archive stream, and unzips in-memory.
   - Parses the XML DOM via `ingestion/log_normalizer/junit_parser.py`.
2. **Git Context Retrieval**:
   - Queries `GET /repos/{owner}/{repo}/commits/{head_sha}`.
   - Extracts commit author, timestamp, message, changed files, addition/deletion counts, and patches.
3. **Log Sanitization & Normalization**:
   - Strips ANSI color codes, ISO runner timestamps, memory addresses (`0x7f...`), and UUIDs.
   - Redacts leaked tokens (`ghp_...`, AWS keys) before database insertion.
   - Generates deterministic SHA-256 error fingerprints.
4. **Autonomous RCA Triage**:
   - For every failed test case, `TriageOrchestrator` gathers an immutable evidence bundle (`EvidenceBundle`).
   - `HypothesisEvaluator` evaluates hypotheses $H_1$ through $H_7$.
   - Agent cites only valid evidence IDs; refusal logic triggers if evidence IDs are absent.
   - Proposes remediation with human-approval gate (`RemediationStatus.PENDING_APPROVAL`).

---

## 6. Live End-to-End Verification Proof Summary

The end-to-end flow was verified live against the actual connected repository `https://github.com/Dhanamukilan/Hackwave2.0`.

### Real Execution Records

| Entity | Real Value / Identifier |
| :--- | :--- |
| **Repository** | `https://github.com/Dhanamukilan/Hackwave2.0` |
| **Target Branch** | `main` |
| **Commit SHA** | `744275d56d6eb90d6340d95092e447aee2ca9299` |
| **GitHub Actions Run ID** | `36118968273` |
| **Run URL** | [Actions Run 36118968273](https://github.com/Dhanamukilan/Hackwave2.0/actions/runs/36118968273) |
| **JUnit Artifact ID** | `10855937148` (`test-results.zip`) |
| **GitHub Webhook Delivery ID** | `3844701747532537856` |
| **HMAC Signature** | `sha256=5f3f4efd81f3095a4846f24c8b88ed1851b1f871ca9f4a1e08c8271be57b2b07` |
| **Failed Test Case** | `tests/unit/test_payment_gateway.py::test_payment_gateway_charge_authorization` |
| **Error Type** | `AssertionError` (Gateway Timeout HTTP 500) |
| **Database Build ID** | `a36a4a1a-2d03-47c3-a363-9b29fea90818` |
| **RCA Investigation ID** | `e9812f42-3dba-4e80-a38e-6d132506e920` |
| **Confirmed Hypothesis** | **H1: Code Regression** |
| **Confidence Level** | **HIGH** |
| **Cited Evidence IDs** | `['EV-CHAN-06', 'EV-GIT_-05', 'EV-TEST-01', 'EV-FAIL-02', 'EV-FLAK-03', 'EV-ENVI-04', 'EV-RUNT-07']` |
| **Remediation Action** | `CODE_FIX` (Status: `PENDING_APPROVAL`) |

Full raw webhook payload and investigation metadata are archived in `docs/runbooks/real-run-proof.json`.
