# AG004 — CI/CD Failure Triage and Flaky-Test Predictor
### Corrected Problem Statement & Implementation-Ready Solution

**Target implementation:** Antigravity (agentic IDE), against a real GitHub repository
**LLM reasoning layer:** local open-source model (no hosted API dependency)
**Deployment target:** Docker Compose for local/dev, Kubernetes manifests included for later

---

## 1. Problem Statement (unchanged in substance)

**Domain:** Agentic & Generative AI — IT Operations / DevOps

Modern development teams run hundreds to thousands of automated tests per code change.
When CI/CD pipelines fail, the failure could be any of:

- a genuine software regression
- a flaky (intermittent/unreliable) test
- an infrastructure or environment problem
- a network or dependency failure
- a timeout or resource-exhaustion problem
- a test-data problem
- a duplicate manifestation of a failure already seen elsewhere

Today, developers manually read large CI logs, cross-check prior failures, inspect the diff,
guess the affected component, guess the responsible owner, and decide whether the failure
even matters. This is slow and inconsistent.

**Goal:** build a real, working CI/CD Failure Intelligence Platform that automates this
investigation end-to-end — not a chatbot wrapped around raw logs.

---

## 2. What Was Corrected From the Original Spec, and Why

The original spec is architecturally sound but was written assuming unlimited implementation
time and a hosted-LLM API. Corrections made for a buildable, real (non-fake) hackathon system:

| # | Original | Correction | Reason |
|---|---|---|---|
| 1 | LLM via hosted API (e.g. Anthropic API) | **Local open-source LLM** (Ollama, OpenAI-compatible endpoint — e.g. `llama3.1:8b`, `qwen2.5:7b-instruct`, or `mistral`) | Chosen for this build. No external API key dependency; runs entirely in your infra. Swappable via one config value if you later want a larger hosted model for better RCA quality. |
| 2 | Neo4j listed as an option | Keep as **optional, not default** | Original spec already says "use only if the implementation genuinely benefits" — confirmed: Postgres foreign keys are sufficient for the evidence graph at hackathon scale; add Neo4j only if you build a graph-exploration UI later. |
| 3 | Full Kubernetes + OpenTelemetry + Fluent Bit runtime observability as day-one requirement | **Docker Compose is the default runtime; K8s manifests are written but optional to actually deploy** | You need one running, demoable system before a multi-node cluster. K8s/OTel stay in the architecture and folder structure so the path to production is real, not hand-waved. |
| 4 | "GitHub Actions initially, Jenkins adapter optionally" | Confirmed, and made concrete: implement `CIAdapter` interface first against **your real GitHub repo**, Jenkins adapter stays a stub implementing the same interface | You confirmed a real GitHub repo — this is now a hard requirement of the ingestion layer, not a nice-to-have. |
| 5 | Vector DB: "Qdrant or equivalent" | **Qdrant**, run via Docker Compose alongside Postgres | Concrete choice needed for implementation; Qdrant has a simple local Docker image and a clean Python client. |
| 6 | ML models: "XGBoost/LightGBM or equivalent" | **LightGBM** for classification + flaky prediction (faster to train on small hackathon datasets, no build-toolchain issues in containers) | Concrete choice; XGBoost is an easy swap if preferred later, both share a scikit-learn-compatible API. |
| 7 | Evaluation section allowed "never invent performance numbers" but gave no fallback for cold-start | **Explicit rule added:** until your real GitHub repo has enough historical runs, all reported metrics come from the labeled `datasets/synthetic` benchmark and must be tagged `[synthetic benchmark]` in the UI and reports. Once ≥ N real runs exist (config `MIN_REAL_SAMPLES`, default 200), metrics switch to real-data evaluation automatically. | Prevents the two failure modes explicitly banned in the spec: fabricated numbers, and silently mixing synthetic with real results. |
| 8 | Agent tool list given without execution boundaries | **Explicit tool contract added** (below) | Needed so "agents must not invent evidence" is enforced in code, not just prose. |
| 9 | Security section listed requirements without an implementation home | Mapped 1:1 to `backend/app/middleware`, `backend/app/core/security.py`, `config/` (see §7) | Makes the requirement checkable during implementation review. |

Everything else in the original spec (failure model, severity/confidence separation, hypothesis
list H1–H7, fingerprinting approach, frontend sections, implementation order) is preserved as-is
— it was already correct and buildable.

---

## 3. Architecture (confirmed, with the above substitutions)

```text
GitHub (real repo)
   ↓ webhook (push / pull_request / workflow_run / check_run)
GitHub Actions (CI/CD)
   ↓
Build / Test / Deploy
   ↓
Evidence Collection
 ├─ CI logs (GitHub API)
 ├─ Test results (JUnit/JSON)
 ├─ Git commits/diffs (GitHub API)
 ├─ Deployment events
 ├─ Container/K8s logs (optional, once deployed)
 └─ Metrics/traces (OTel, optional)
   ↓
Log/Test Normalization  →  Failure Fingerprinting
   ↓
 ┌────────────┬───────────────┬──────────────────┐
 Test History   Git Changes     Similar Failures (Qdrant)
 └────────────┴───────────────┴──────────────────┘
   ↓
ML/NLP Intelligence
 ├─ Failure Classification (LightGBM)
 ├─ Flaky-Test Prediction (LightGBM, time-aware split)
 └─ Failure Clustering (fingerprint + Sentence-Transformers embeddings)
   ↓
Severity Engine  →  Evidence Engine
   ↓
Agentic Layer (tool-using, Postgres/Qdrant-backed, no invented evidence)
 Log Agent → History Agent → Git Agent → Component/Owner Agent → Evidence Agent
   ↓
RCA Agent (H1–H7 hypothesis evidence-for/against)  →  Remediation Agent
   ↓
Local LLM (Ollama) — reasoning over retrieved evidence only
   ↓
Evidence-backed RCA + Recommended Action
   ↓
Human Approval  →  CI Re-run  →  Deployment (Docker → K8s optional)
   ↓
Runtime Observability (optional, OTel/Fluent Bit)  →  Feedback → Historical Learning
```

---

## 4. Agent Tool Contract (enforced, not just declared)

Every tool below **must** query real Postgres/Qdrant data and return either data or an explicit
`no_evidence_found`. Agents are only allowed to state a conclusion citing a tool's returned
`evidence_id`s — no free-floating claims.

```text
get_test_history(test_id)            -> execution records, chronological
get_failure_history(fingerprint_id)  -> prior occurrences of this fingerprint
search_similar_failures(embedding)   -> top-k Qdrant matches + similarity score
get_commit_diff(commit_sha)          -> changed files + diff hunks
get_recent_commits(repo, since)      -> commit list
get_changed_files(commit_sha)        -> file paths + component mapping
get_component_owner(component_id)    -> owner/team record
get_environment_history(test_id)     -> runner OS/version/env variance
get_deployment_history(service_id)   -> recent deploys, correlated timing
calculate_flakiness(test_id)         -> derived features (not a model call)
get_runtime_evidence(service_id)     -> OTel/log evidence if deployed
```

Enforcement point: `agents/orchestrator` builds the evidence bundle from tool outputs *before*
constructing the LLM prompt; the LLM prompt template forbids adding claims not present in the
bundle, and the RCA Agent output schema requires an `evidence_ids: []` field per hypothesis.

---

## 5. Data Model (Postgres — confirmed from spec)

`users, repositories, pipelines, builds, test_runs, tests, failures, fingerprints, commits,
changed_files, components, owners, deployments, predictions, investigations, remediations, feedback`

Vector store (Qdrant): one collection, `failure_embeddings`, payload = `{fingerprint_id,
failure_id, test_id, classification, created_at}`, vector = Sentence-Transformers embedding of
the normalized error signature + stack-trace summary.

---

## 6. Failure Model (confirmed from spec — kept separate, not merged)

- **Classification:** `REGRESSION | FLAKY_TEST | INFRASTRUCTURE | ENVIRONMENT | DEPENDENCY | NETWORK | TIMEOUT | BUILD_FAILURE | TEST_DATA | UNKNOWN`
- **Flakiness** — likelihood the failure is intermittent (independent score)
- **Regression probability** — likelihood a code change caused it (independent score)
- **Severity** — `NORMAL | LOW | MEDIUM | HIGH | CRITICAL` (impact *if* real)
- **RCA confidence** — `LOW | MEDIUM | HIGH` (strength of evidence)

These four are never combined into a single composite score anywhere in the system.

---

## 7. Security Implementation Map

| Requirement | Where |
|---|---|
| Auth | `backend/app/core/security.py` (JWT) |
| RBAC | `backend/app/core/security.py` + role checks in `backend/app/api` |
| Webhook verification | `backend/app/middleware` (GitHub HMAC-SHA256) |
| Secrets | `.env` (gitignored) / K8s Secrets, never hardcoded — see `.env.example` |
| Input validation | Pydantic schemas in `backend/app/schemas` |
| Log sanitization | `ingestion/log_normalizer` strips secrets/tokens before storage |
| Audit logging | `backend/app/middleware` writes to `audit_log` table |
| Rate limiting | `backend/app/middleware` |
| Allowlisted agent tools | `agents/tools` — no dynamic tool registration, no shell exec |
| Human approval gate | `investigations.status` state machine — remediation cannot trigger a re-run or deploy without an explicit approve action |

---

## 8. Evaluation Rules (corrected — cold-start handling added)

- Classification: precision / recall / F1 / confusion matrix
- Prediction: precision/recall, PR-AUC or ROC-AUC, calibration where practical
- Clustering: silhouette score
- Component/Owner ID: top-1 / top-3 accuracy
- **Cold-start rule (new):** metrics computed on `datasets/synthetic` are labeled
  `[synthetic benchmark]` everywhere they're displayed, until `MIN_REAL_SAMPLES` real pipeline
  runs exist, at which point evaluation automatically switches to real-data results.
- No fabricated numbers under any circumstance — if a metric can't be computed yet, the UI
  shows "insufficient data" rather than a placeholder number.

---

## 9. Build Order (confirmed from spec, unchanged — keep the app runnable at every step)

1. Architecture + repository structure *(this document + the scaffold delivered alongside it)*
2. Sample application/repository (your real GitHub repo)
3. GitHub integration (App/PAT + webhook)
4. GitHub Actions CI/CD (`.github/workflows/ci.yml`)
5. Test execution and failure ingestion
6. PostgreSQL data layer
7. Log parsing/normalization
8. Failure fingerprinting
9. Failure classification
10. Flaky-test prediction
11. Failure clustering + vector retrieval (Qdrant)
12. Git/code-change correlation
13. Component/owner mapping
14. Severity engine
15. Evidence engine
16. Agentic investigation
17. Local-LLM RCA + remediation
18. React dashboard
19. Dockerization (Compose)
20. Kubernetes manifests (optional to actually deploy)
21. OpenTelemetry/runtime monitoring (optional)
22. Feedback loop
23. Evaluation framework
24. End-to-end demo scenarios (7 required scenarios)
25. Security hardening
26. Documentation

---

## 10. Non-Negotiable Rules (unchanged)

Do **not** build: a generic chatbot · a static dashboard · an LLM-only log analyzer ·
hardcoded predictions · fake CI results · fake ML metrics · fabricated evidence ·
static RCA responses · arbitrary AI-generated numbers.

Every important result must trace to real data or clearly-labeled synthetic benchmark data.

---

## 11. Questions the finished system must answer

What failed? · Why did it fail? · Is it a real regression or a flaky failure? ·
Has it happened before? · What changed? · Which component is affected? ·
Who should investigate it? · How severe is it? · What evidence supports the conclusion? ·
What should the developer do next? · Did the remediation actually solve the problem?

---

*Companion deliverable: `ag004-project-structure.zip` — the folder scaffold with a purpose-explaining
README in every directory, root `README.md`, `.env.example`, `docker-compose.yml` skeleton, `.gitignore`,
and a sample `.github/workflows/ci.yml`, ready to open in Antigravity.*
