from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from backend.app.models.base import FailureClassification, SeverityLevel

class FingerprintResponse(BaseModel):
    id: str
    hash_value: str
    error_type: str
    normalized_message: str
    location: Optional[str]
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FailureResponse(BaseModel):
    id: str
    test_run_id: str
    test_id: str
    fingerprint_id: Optional[str]
    error_type: str
    raw_message: str
    normalized_message: str
    raw_stack_trace: Optional[str]
    normalized_stack_trace: Optional[str]
    classification: FailureClassification
    classification_confidence: float
    flakiness_score: float
    regression_prob: float
    severity: SeverityLevel
    ci_provider: Optional[str] = "github_actions"
    pipeline_name: Optional[str] = "CI"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class IngestExecutionRequest(BaseModel):
    repository_name: str
    pipeline_name: str
    commit_sha: str
    branch: str = "main"
    junit_xml: Optional[str] = None
    json_report: Optional[str] = None
    runner_os: str = "ubuntu-latest"
    runner_version: str = "22.04"
