import re
import hashlib
from typing import Dict, Any, Tuple, Optional

# Regular expressions for sanitization and normalization
ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
TIMESTAMP_REGEX = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?|\d{2}:\d{2}:\d{2}(?:\.\d+)?)\b"
)
HEX_MEMORY_REGEX = re.compile(r"0x[0-9a-fA-F]{4,16}\b")
UUID_REGEX = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
IPV4_REGEX = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?::\d{1,5})?\b")
RUNNER_PATH_REGEX = re.compile(
    r"(?:/home/runner/work/[^\s\"\'\:]+|/var/lib/jenkins/[^\s\"\'\:]+|[A-Za-z]:\\[^\s\"\'\:]+)"
)

# Secret masking patterns
SECRET_TOKEN_PATTERNS = [
    re.compile(r"(?i)(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,255}"),
    re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{15,}"),
    re.compile(r"(?i)(api[_\-]?key|secret|password|auth[_\-]?token|access[_\-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
]

ERROR_PATTERN = re.compile(
    r"(?:(?P<error_type>[A-Za-z]+(?:Error|Exception|Failure|Fault|Timeout))\s*:\s*(?P<msg>[^\n\r]+))|"
    r"(?:FAILED\s+(?P<pytest_file>[^\s\:]+)(?:::(?P<pytest_test>[^\s]+))?\s*-\s*(?P<pytest_msg>[^\n\r]+))|"
    r"(?:FAIL:\s*(?P<test_name>[^\s]+)\s*\((?P<test_suite>[^\)]+)\))"
)

LOCATION_PATTERN = re.compile(
    r'(?:File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+))|'
    r'(?:at\s+(?P<java_class>[a-zA-Z0-9_\.]+)\((?P<java_file>[a-zA-Z0-9_]+\.java):(?P<java_line>\d+)\))|'
    r'(?:at\s+(?:async\s+)?(?P<js_func>[a-zA-Z0-9_\.]+)\s*\((?P<js_file>[^:\)]+):(?P<js_line>\d+):(?P<js_col>\d+)\))'
)

def sanitize_secrets(text: str) -> str:
    """Strips secrets, passwords, tokens before any storage or processing."""
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_TOKEN_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized

def normalize_log_text(text: str) -> str:
    """
    Strips ANSI codes, timestamps, memory addresses, UUIDs, IPs, and local paths.
    """
    if not text:
        return ""
    
    # 1. Sanitize secrets
    normalized = sanitize_secrets(text)

    # 2. Strip ANSI
    normalized = ANSI_REGEX.sub("", normalized)

    # 3. Strip Timestamps
    normalized = TIMESTAMP_REGEX.sub("<TIMESTAMP>", normalized)

    # 4. Mask Hex addresses
    normalized = HEX_MEMORY_REGEX.sub("<MEM_ADDR>", normalized)

    # 5. Mask UUIDs
    normalized = UUID_REGEX.sub("<UUID>", normalized)

    # 6. Mask IPs
    normalized = IPV4_REGEX.sub("<IP_ADDR>", normalized)

    # 7. Normalize file paths to relative basenames
    normalized = RUNNER_PATH_REGEX.sub("<PATH>", normalized)

    # 8. Collapse repeated whitespace
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()

def extract_error_signature(log_text: str) -> Dict[str, Any]:
    """
    Extracts the canonical error type, normalized message, location, and stack trace summary.
    """
    clean_text = sanitize_secrets(log_text)
    
    error_type = "UnknownError"
    message = "No specific error message identified"
    location = None

    # Search for error patterns
    match = ERROR_PATTERN.search(clean_text)
    if match:
        groups = match.groupdict()
        if groups.get("error_type") and groups.get("msg"):
            error_type = groups["error_type"].strip()
            message = groups["msg"].strip()
        elif groups.get("pytest_msg"):
            error_type = "PytestAssertionFailure"
            message = groups["pytest_msg"].strip()
            if groups.get("pytest_file"):
                location = f"{groups['pytest_file']}::{groups.get('pytest_test', '')}"
        elif groups.get("test_name"):
            error_type = "UnitTestFailure"
            message = f"{groups['test_name']} in {groups.get('test_suite')}"

    # Search for location
    if not location:
        loc_match = LOCATION_PATTERN.search(clean_text)
        if loc_match:
            loc_dict = loc_match.groupdict()
            if loc_dict.get("file"):
                location = f"{loc_dict['file']}:{loc_dict['line']}"
            elif loc_dict.get("java_file"):
                location = f"{loc_dict['java_file']}:{loc_dict['java_line']}"
            elif loc_dict.get("js_file"):
                location = f"{loc_dict['js_file']}:{loc_dict['js_line']}"

    normalized_msg = normalize_log_text(message)
    normalized_full = normalize_log_text(clean_text)

    fingerprint_hash = generate_fingerprint(error_type, normalized_msg, location)

    return {
        "error_type": error_type,
        "raw_message": message,
        "normalized_message": normalized_msg,
        "location": location,
        "normalized_text": normalized_full,
        "fingerprint_hash": fingerprint_hash,
    }

def generate_fingerprint(error_type: str, normalized_message: str, location: Optional[str] = None) -> str:
    """
    Generates a deterministic SHA-256 fingerprint from error type, message, and location.
    """
    canonical_tokens = [
        error_type.strip().lower(),
        (location or "unknown_loc").strip().lower(),
        # Keep only word characters from message for stability across slight phrasing diffs
        re.sub(r"[^a-zA-Z0-9]", "", normalized_message.lower())[:120]
    ]
    raw_key = "|".join(canonical_tokens)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
