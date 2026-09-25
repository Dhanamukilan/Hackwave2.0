import re
from typing import Dict, Any, List
import numpy as np

KEYWORD_FLAGS = {
    "is_assertion": re.compile(r"(?i)\b(assert|assertionerror|assertionfailure|pytestassertionfailure|expected|got|mismatch)\b"),
    "is_timeout": re.compile(r"(?i)\b(timeout|timed out|deadline exceeded|timeoutexception)\b"),
    "is_network": re.compile(r"(?i)\b(connection\s*error|connection\s*refused|failed to connect|max retries exceeded|econnreset|ehostunreach|getaddrinfo|network is unreachable|socket|http\s*error|503\b|502\b|504\b|remotedisconnected)\b"),
    "is_infra": re.compile(r"(?i)\b(oomkiller|out of memory|no space left on device|disk full|runner lost|agent died|runnerdiederror|memoryerror)\b"),
    "is_env": re.compile(r"(?i)\b(env var|missing environment|not found in path|permission denied|chmod|libc|environmenterror)\b"),
    "is_dependency": re.compile(r"(?i)\b(modulenotfounderror|importerror|package not found|could not find a version that satisfies|npm err|packagenotfounderror)\b"),
    "is_build": re.compile(r"(?i)\b(syntaxerror|compilation error|build failed|typeerror: cannot read|cannot find symbol|buildfailure|compileerror|typescripterror)\b"),
    "is_test_data": re.compile(r"(?i)\b(fixture not found|foreign key constraint|integrityerror|duplicate key|database is locked|dataerror)\b"),
}

def extract_failure_features(
    raw_message: str,
    normalized_message: str,
    raw_stack_trace: str,
    error_type: str,
    duration_seconds: float = 0.0,
    test_run_count: int = 1,
    test_failure_rate: float = 0.0,
    test_flakiness_score: float = 0.0,
    occurrence_count: int = 1
) -> Dict[str, float]:
    """
    Extracts numerical feature vector for classification and flakiness scoring.
    """
    combined_text = f"{error_type} {normalized_message} {raw_stack_trace}"
    
    features = {
        "log_length": float(len(combined_text)),
        "stack_trace_lines": float(len(raw_stack_trace.splitlines())) if raw_stack_trace else 0.0,
        "duration_seconds": float(duration_seconds),
        "test_run_count": float(test_run_count),
        "test_failure_rate": float(test_failure_rate),
        "test_flakiness_score": float(test_flakiness_score),
        "fingerprint_occurrences": float(occurrence_count),
    }

    # Keyword indicators
    for flag_name, pattern in KEYWORD_FLAGS.items():
        features[flag_name] = 1.0 if pattern.search(combined_text) else 0.0

    return features

def extract_flaky_test_features(
    run_history: List[Dict[str, Any]],
    test_age_days: float = 30.0
) -> Dict[str, float]:
    """
    Extracts time-aware features for flaky-test prediction:
    - flip_rate: transitions between PASS and FAIL
    - failure_rate: ratio of failed runs
    - duration_variance: std dev of execution time
    - total_runs: number of observed executions
    - recent_flips: flip rate in last 10 runs
    """
    if not run_history:
        return {
            "flip_rate": 0.0,
            "failure_rate": 0.0,
            "duration_variance": 0.0,
            "total_runs": 0.0,
            "recent_flips": 0.0,
            "test_age_days": test_age_days,
        }

    statuses = [r.get("status", "PASSED").upper() for r in run_history]
    durations = [float(r.get("duration_seconds", 0.0)) for r in run_history]

    # Calculate status flips (PASS -> FAIL or FAIL -> PASS)
    flips = 0
    for i in range(1, len(statuses)):
        if statuses[i] != statuses[i - 1]:
            flips += 1

    total_runs = len(statuses)
    flip_rate = flips / (total_runs - 1) if total_runs > 1 else 0.0
    failure_rate = sum(1 for s in statuses if s == "FAILED") / total_runs

    # Recent flips (last 10 runs)
    recent = statuses[-10:]
    recent_flips = 0
    for i in range(1, len(recent)):
        if recent[i] != recent[i - 1]:
            recent_flips += 1
    recent_flip_rate = recent_flips / (len(recent) - 1) if len(recent) > 1 else 0.0

    dur_variance = float(np.var(durations)) if len(durations) > 1 else 0.0

    return {
        "flip_rate": flip_rate,
        "failure_rate": failure_rate,
        "duration_variance": dur_variance,
        "total_runs": float(total_runs),
        "recent_flips": recent_flip_rate,
        "test_age_days": test_age_days,
    }
