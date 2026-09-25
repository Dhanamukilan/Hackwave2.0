# AG004 — Live Demo Scenarios Runbook

This runbook describes the 7 end-to-end demo scenarios built into the AG004 Failure Intelligence Platform. Each scenario can be inspected in the dashboard or executed directly via its standalone runner script.

---

## Scenario 01: Genuine Code Regression
- **Folder:** `demo_repo_scenarios/01_regression/`
- **Execution Script:** `python demo_repo_scenarios/01_regression/run_scenario.py`
- **What Happens:**
  - A developer commits a code change in `services/payment/gateway.py` restricting minimum transactions.
  - Test `test_small_amount_charge` fails with `AssertionError: assert 500 == 200`.
  - **Orchestration Output:**
    - Classification: `REGRESSION` (94% regression probability, 5% flakiness).
    - Severity: `HIGH`.
    - Component Mapping: `Payment Gateway` &rarr; Lead Owner `Elena Rostova`.
    - Hypothesis Matrix: **H1 (Code Regression)** confirmed with evidence items `EV-GIT_-05` and `EV-CHAN-06`.
    - Proposed Remediation: `CODE_FIX` patch with human approval gate.

---

## Scenario 02: Flaky Test Identification
- **Folder:** `demo_repo_scenarios/02_flaky_test/`
- **Execution Script:** `python demo_repo_scenarios/02_flaky_test/run_scenario.py`
- **What Happens:**
  - Test `test_cart_concurrency_race` fails intermittently due to lock acquisition timeout.
  - Historical analysis indicates a **flip rate of 72%** across 48 observed runs.
  - **Orchestration Output:**
    - Classification: `FLAKY_TEST` (Flakiness Score: 72%, Regression Prob: 12%).
    - Severity: `LOW`.
    - Hypothesis Matrix: **H2 (Flaky Test)** confirmed.
    - Proposed Remediation: `QUARANTINE_TEST` suggesting quarantine mark to unblock the PR while concurrency is resolved.

---

## Scenario 03: Duplicate & Co-occurring Failures
- **Folder:** `demo_repo_scenarios/03_duplicate_failures/`
- **Execution Script:** `python demo_repo_scenarios/03_duplicate_failures/run_scenario.py`
- **What Happens:**
  - Multiple test runs in separate builds fail with `ConnectionRefusedError: redis-cluster:6379`.
  - The Log Normalizer extracts the normalized signature and generates canonical fingerprint `fp_redis_connection_refused_6379`.
  - Qdrant vector search matches semantic embeddings across runs with >90% cosine similarity.
  - The UI clusters them together, demonstrating that two separate build failures share one root cause.

---

## Scenario 04: Infrastructure Runner Outage
- **Folder:** `demo_repo_scenarios/04_infrastructure_failure/`
- **Execution Script:** `python demo_repo_scenarios/04_infrastructure_failure/run_scenario.py`
- **What Happens:**
  - The test runner is terminated abruptly by host OS `OOMKiller (exit code 137)`.
  - **Orchestration Output:**
    - Classification: `INFRASTRUCTURE` (98% confidence).
    - Severity: `HIGH`.
    - Hypothesis Matrix: **H3 (Infrastructure Outage)** confirmed with zero code diff correlation.
    - Proposed Remediation: Increase runner cgroup memory limits.

---

## Scenario 05: External Dependency & Network Outage
- **Folder:** `demo_repo_scenarios/05_dependency_network_failure/`
- **Execution Script:** `python demo_repo_scenarios/05_dependency_network_failure/run_scenario.py`
- **What Happens:**
  - Downstream payment partner returns `HTTP 503 Service Unavailable`.
  - **Orchestration Output:**
    - Classification: `DEPENDENCY` / `NETWORK`.
    - Regression Probability: 2% (correctly ruled out code regressions).
    - Hypothesis Matrix: **H5 (External Dependency)** confirmed.
    - Proposed Remediation: `RETRY_PIPELINE` once upstream service recovers.

---

## Scenario 06: Build & Toolchain Failure
- **Folder:** `demo_repo_scenarios/06_code_change_failure/`
- **Execution Script:** `python demo_repo_scenarios/06_code_change_failure/run_scenario.py`
- **What Happens:**
  - Build fails during TypeScript compile step before running unit tests (`Cannot find module '@company/core-types'`).
  - **Orchestration Output:**
    - Classification: `BUILD_FAILURE`.
    - Severity: `HIGH` (blocking main pipeline).
    - Hypothesis Matrix: **H7 (Build Toolchain Failure)** confirmed.

---

## Scenario 07: Successful Rerun & Closed Loop
- **Folder:** `demo_repo_scenarios/07_successful_rerun/`
- **Execution Script:** `python demo_repo_scenarios/07_successful_rerun/run_scenario.py`
- **What Happens:**
  - Following human approval of remediation, build #105 executes.
  - **Outcome:** `SUCCESS` (60 / 60 tests passed, 0 failures, 285s duration).
  - Demonstrates verified end-to-end failure resolution.
