import json
import logging
from typing import Dict, Any, List
from backend.app.models.base import RCAConfidence, FailureClassification

logger = logging.getLogger(__name__)

HYPOTHESES_DEFINITIONS = [
    {"id": "H1", "title": "Code Regression", "description": "Recent code change directly introduced a functional regression."},
    {"id": "H2", "title": "Flaky Test", "description": "Intermittent test execution failure due to concurrency, timing, or race conditions."},
    {"id": "H3", "title": "Infrastructure Outage", "description": "Host runner crash, OOM kill, or disk space exhaustion."},
    {"id": "H4", "title": "Environment Variance", "description": "Difference in OS runner version, missing environment variable or permissions."},
    {"id": "H5", "title": "External Dependency / Network", "description": "External third-party API or network socket connectivity failure."},
    {"id": "H6", "title": "Test Data Corruption", "description": "Database constraint violation, missing fixture, or state leakage between tests."},
    {"id": "H7", "title": "Build / Toolchain Failure", "description": "Syntax error, compilation failure, or broken build dependency package."},
]

class HypothesisEvaluator:
    """
    Evaluates hypotheses H1 through H7 strictly against gathered evidence items.
    Enforces evidence ID citations to ensure zero invented claims.
    """

    def evaluate(self, evidence_bundle: Dict[str, Any], classification: str, error_type: str) -> Dict[str, Any]:
        if not evidence_bundle:
            raise ValueError(
                "RCA Agent refuses to output a conclusion: evidence_bundle is missing or empty. Agents must not invent evidence."
            )

        valid_ids_list = evidence_bundle.get("valid_evidence_ids")
        if valid_ids_list is None:
            valid_ids_list = evidence_bundle.get("evidence_ids")

        if not valid_ids_list or len(valid_ids_list) == 0:
            raise ValueError(
                "RCA Agent refuses to output a conclusion: evidence_ids is missing or empty. Agents must not invent evidence."
            )

        valid_ids = set(valid_ids_list)
        items = evidence_bundle.get("evidence_items", [])
        if not items:
            raise ValueError(
                "RCA Agent refuses to output a conclusion: evidence_items is empty. Agents must not invent evidence."
            )

        # Categorize evidence by type
        items_by_type = {}
        for it in items:
            items_by_type.setdefault(it["evidence_type"], []).append(it)

        hypotheses_results = []
        winning_hypothesis = None
        highest_score = -1.0

        for h in HYPOTHESES_DEFINITIONS:
            hid = h["id"]
            title = h["title"]
            supporting = []
            contradicting = []
            score = 0.0

            if hid == "H1":  # Code Regression
                git_items = items_by_type.get("GIT_DIFF", []) + items_by_type.get("CHANGED_FILES", [])
                hist_items = items_by_type.get("TEST_HISTORY", [])
                if git_items:
                    for gi in git_items:
                        supporting.append(gi["evidence_id"])
                        score += 0.4
                if classification == FailureClassification.REGRESSION.value:
                    score += 0.4
                flaky_items = items_by_type.get("FLAKINESS_METRICS", [])
                for fi in flaky_items:
                    if fi.get("data", {}).get("is_intermittent"):
                        contradicting.append(fi["evidence_id"])
                        score -= 0.3

            elif hid == "H2":  # Flaky Test
                flaky_items = items_by_type.get("FLAKINESS_METRICS", [])
                for fi in flaky_items:
                    if fi.get("data", {}).get("is_intermittent") or fi.get("data", {}).get("flakiness_score", 0) >= 0.35:
                        supporting.append(fi["evidence_id"])
                        score += 0.7
                if classification == FailureClassification.FLAKY_TEST.value:
                    score += 0.3

            elif hid == "H3":  # Infrastructure Outage
                if classification == FailureClassification.INFRASTRUCTURE.value:
                    score += 0.8
                for it in items:
                    if any(k in str(it.get("data", "")).lower() for k in ["oom", "runner died", "disk full"]):
                        supporting.append(it["evidence_id"])
                        score += 0.3

            elif hid == "H4":  # Environment Variance
                env_items = items_by_type.get("ENVIRONMENT_VARIANCE", [])
                for ei in env_items:
                    if ei.get("data", {}).get("variance_detected"):
                        supporting.append(ei["evidence_id"])
                        score += 0.6
                if classification == FailureClassification.ENVIRONMENT.value:
                    score += 0.4

            elif hid == "H5":  # Dependency / Network
                if classification in [FailureClassification.NETWORK.value, FailureClassification.DEPENDENCY.value]:
                    score += 0.7
                for it in items:
                    if any(k in str(it.get("data", "")).lower() for k in ["connection refused", "503", "timeout", "socket"]):
                        supporting.append(it["evidence_id"])
                        score += 0.3

            elif hid == "H6":  # Test Data
                if classification == FailureClassification.TEST_DATA.value:
                    score += 0.8
                for it in items:
                    if "foreign key" in str(it.get("data", "")).lower() or "integrity" in str(it.get("data", "")).lower():
                        supporting.append(it["evidence_id"])
                        score += 0.3

            elif hid == "H7":  # Build Failure
                if classification == FailureClassification.BUILD_FAILURE.value:
                    score += 0.9
                for it in items:
                    if "syntaxerror" in str(it.get("data", "")).lower() or "compile" in str(it.get("data", "")).lower():
                        supporting.append(it["evidence_id"])
                        score += 0.3

            # Deduplicate and filter to strictly valid evidence IDs
            supporting = [eid for eid in set(supporting) if eid in valid_ids]
            contradicting = [eid for eid in set(contradicting) if eid in valid_ids]

            status = "REFUTED"
            if score >= 0.5 and supporting:
                status = "CONFIRMED"
            elif score > 0.1:
                status = "INSUFFICIENT_EVIDENCE"

            if score > highest_score and status == "CONFIRMED":
                highest_score = score
                winning_hypothesis = hid

            hypotheses_results.append({
                "hypothesis_id": hid,
                "title": title,
                "status": status,
                "score": round(max(0.0, min(1.0, score)), 2),
                "supporting_evidence_ids": supporting,
                "contradicting_evidence_ids": contradicting,
                "reasoning": f"Evaluated based on cited evidence: {supporting or 'None'}."
            })

        # Confidence determination
        confidence = RCAConfidence.LOW
        if highest_score >= 0.75:
            confidence = RCAConfidence.HIGH
        elif highest_score >= 0.5:
            confidence = RCAConfidence.MEDIUM

        # If no hypothesis was confirmed, pick the one with the highest score
        if not winning_hypothesis and hypotheses_results:
            best = max(hypotheses_results, key=lambda h: h["score"])
            winning_hypothesis = best["hypothesis_id"]
            confidence = RCAConfidence.LOW

        return {
            "winning_hypothesis": winning_hypothesis or "INCONCLUSIVE",
            "confidence": confidence.value,
            "hypotheses_matrix": hypotheses_results
        }

hypothesis_evaluator = HypothesisEvaluator()
