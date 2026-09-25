# Model Evaluation & Benchmark Report: AG004

## 1. Evaluation Methodology & Feasibility Bar

Per the AG004 Problem Statement & Specification (§6 & §11), the feasibility bar requires real, measurable machine learning models evaluated against structured ground-truth datasets, strictly separated from generative summaries or dashboards alone.

### Measured Capabilities

| Model / Decision Task | Model Architecture | Primary Metrics | Provenance Status |
| :--- | :--- | :--- | :--- |
| **Failure Classification** | LightGBM / GBDT (10 classes) + TF-IDF error signature | Precision, Recall, Weighted F1, Confusion Matrix | `[synthetic benchmark]` (17 real samples < 200 threshold) |
| **Flaky-Test Prediction** | LightGBM with time-aware execution split | ROC-AUC, PR-AUC, Precision, Recall, Brier score | `[synthetic benchmark]` |
| **Failure Clustering** | Dense sentence-transformer embeddings + Qdrant | Silhouette Score, Cosine Distance, Inter-cluster Separation | `[synthetic benchmark]` |
| **Component & Owner ID** | Path pattern matcher + ownership mapping table | Top-1 Accuracy, Top-3 Accuracy | `[synthetic benchmark]` |

---

## 2. Cold-Start Governance Policy

The platform enforces a deterministic cold-start policy (`backend/app/core/config.py:MIN_REAL_SAMPLES = 200`):
- When total verified real test execution records in PostgreSQL are `< 200` or human feedback samples `< 50`, all metrics returned by `/api/v1/ml/metrics` are evaluated against the curated benchmark dataset and labeled with `[synthetic benchmark]`.
- Once production history exceeds `200` runs and user feedback accumulates, the evaluator automatically pivots to real historical metrics labeled `[real production data]`.
- Metrics are never invented or hardcoded in presentation layers.

Current System State:
- **Real Production Builds in DB:** 17 builds (from live GitHub Actions runs `36118422497` & `36118968273`, plus live Jenkins ingestion)
- **Active Evaluator Provenance:** `synthetic_benchmark` (`[synthetic benchmark]`)

---

## 3. Measured Metric Values

### 3.1 Failure Classification (LightGBM)

Evaluated across 10 failure categories: `REGRESSION`, `FLAKY_TEST`, `INFRASTRUCTURE`, `ENVIRONMENT`, `DEPENDENCY`, `NETWORK`, `TIMEOUT`, `BUILD_FAILURE`, `TEST_DATA`, `UNKNOWN`.

- **Weighted Precision:** `0.942` `[synthetic benchmark]`
- **Weighted Recall:** `0.934` `[synthetic benchmark]`
- **Weighted F1-Score:** `0.934` `[synthetic benchmark]`
- **Evaluation Samples:** `76` held-out test samples across all 10 canonical failure classes
- **Confusion Matrix:**
  ```text
  [[8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
   [0, 6, 0, 0, 0, 0, 2, 0, 0, 0],
   [0, 0, 7, 0, 0, 0, 0, 0, 0, 1],
   [0, 0, 0, 8, 0, 0, 0, 0, 0, 0],
   [0, 0, 0, 0, 8, 0, 0, 0, 0, 0],
   [0, 0, 0, 0, 0, 8, 0, 0, 0, 0],
   [0, 0, 0, 0, 0, 0, 8, 0, 0, 0],
   [1, 0, 0, 0, 0, 0, 0, 7, 0, 0],
   [0, 0, 0, 0, 0, 0, 0, 0, 8, 0],
   [0, 0, 0, 1, 0, 0, 0, 0, 0, 3]]
  ```

### 3.2 Flaky-Test Prediction (LightGBM Temporal Split)

Evaluated on time-aware historical sequences using derived features (`flip_rate`, `failure_rate`, `duration_variance`, `total_runs`, `recent_flips`, `test_age_days`):

- **ROC-AUC:** `1.000` `[synthetic benchmark]`
- **PR-AUC:** `1.000` `[synthetic benchmark]`
- **Precision:** `0.940` `[synthetic benchmark]`
- **Recall:** `0.910` `[synthetic benchmark]`

### 3.3 Semantic Clustering (Qdrant & Vector Embeddings)

Evaluated using KMeans clustering over dense normalized failure embeddings:

- **Silhouette Score:** `0.740` `[synthetic benchmark]`
- **Interpretation:** Clusters demonstrate strong inter-cluster separation ($>0.70$), successfully grouping duplicate stack traces and related timeout cascades.

### 3.4 Component & Owner Identification

Evaluated by matching commit diff file changes and stack trace origin paths against component ownership graphs:

- **Top-1 Accuracy:** `0.920` `[synthetic benchmark]`
- **Top-3 Accuracy:** `0.980` `[synthetic benchmark]`

---

## 4. Evidence-Based Summary Generator Verification

The generative AI layer (`agents/rca_agent/hypothesis_evaluator.py` and `agents/llm/client.py`) operates under strict constraints:
1. **Zero Raw Logs:** The LLM receives only structured evidence bundles (`EvidenceBundle`), containing tool-collected metrics, diffs, and historical data.
2. **Mandatory Evidence Citation:** Every claim must cite an evidence ID from `valid_evidence_ids` (e.g., `EV-CHAN-06`, `EV-GIT_-05`).
3. **Refusal Mechanism:** If `evidence_ids` is missing or empty, the agent refuses to output a conclusion (`ValueError: RCA Agent refuses to output a conclusion: evidence_ids is missing or empty. Agents must not invent evidence`). This is verified by `tests/unit/test_agents.py::test_rca_agent_refuses_conclusion_with_empty_or_missing_evidence_ids`.
