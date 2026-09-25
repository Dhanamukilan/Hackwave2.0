# AG004 — Build Order & Architecture Specification

This document records the exact 26-step build order followed during the implementation of the AG004 CI/CD Failure Intelligence Platform, matching Section 9 of the solution specification.

---

## Completed Phases

1. **Architecture & Repository Structure:** Full preservation of 16 modular directories.
2. **Sample Application & Repository Data:** Realistic microservices repository with components, owners, commits, and diffs.
3. **GitHub Integration:** GitHub Actions adapter with REST API integration and simulated fallback.
4. **CI/CD Workflows:** `.github/workflows/ci.yml` supporting JUnit XML and JSON test artifact collection.
5. **Ingestion & Normalizer:** Log normalizer with ANSI stripping, timestamp replacement, UUID/path/IP masking, secret sanitization, and JUnit XML/JSON parser.
6. **Data Layer:** PostgreSQL DDL schema + SQLite fallback with 18 SQLAlchemy models.
7. **Failure Fingerprinting:** SHA-256 canonical error signature hashing.
8. **Failure Classification:** LightGBM / Random Forest hybrid classifier supporting the 10-class taxonomy.
9. **Flaky-Test Prediction:** Time-aware LightGBM predictor estimating independent flakiness score from flip rates.
10. **Failure Clustering & Vector Retrieval:** Qdrant vector store indexing normalized error embeddings with semantic similarity queries.
11. **Git Correlation:** Blame, diff hunks, and component-to-codeowner mapping.
12. **Severity Engine:** Independent impact assessment from `NORMAL` to `CRITICAL`.
13. **Evidence Engine:** Structured immutable evidence bundles with verified evidence IDs.
14. **Agentic Layer:** 11 Allowlisted tools, Triage Orchestrator, RCA Agent (H1–H7 matrix), and Remediation Agent with human approval gate.
15. **Local LLM Layer:** Ollama / OpenAI-compatible endpoint with deterministic fallback reasoner.
16. **React Dashboard:** Modern Tailwind CSS SPA with Dashboard, PipelineDetail, FailureInvestigation, RCAView, and SettingsRBAC.
17. **Dockerization:** Complete `docker-compose.yml`, `backend/Dockerfile`, and `frontend/Dockerfile`.
18. **Kubernetes Manifests:** Base deployment, services, configmap, and kustomization in `deployment/k8s/base/`.
19. **Observability:** OpenTelemetry collector configuration and runtime telemetry mocks.
20. **Continuous Feedback:** Human verification and calibration loop.
21. **Evaluation Framework:** Ground truth evaluation with strict Section 8 cold-start provenance tagging (`[synthetic benchmark]`).
22. **7 Demo Scenarios:** Complete scripted scenarios with individual runners and seed data.
23. **Security Hardening:** JWT tokens, RBAC permissions, timing-safe webhook HMAC verification, and audit logging.
24. **Testing Suite:** Comprehensive pytest unit and integration tests passing at 100%.
