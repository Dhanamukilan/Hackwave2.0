from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from backend.app.models.base import BuildStatus

class RepositoryResponse(BaseModel):
    id: str
    name: str
    full_name: str
    default_branch: str
    clone_url: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PipelineResponse(BaseModel):
    id: str
    repository_id: str
    name: str
    workflow_path: str
    provider: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BuildResponse(BaseModel):
    id: str
    pipeline_id: str
    commit_sha: str
    branch: str
    build_number: int
    status: BuildStatus
    trigger: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: float
    model_config = ConfigDict(from_attributes=True)

class TestRunResponse(BaseModel):
    id: str
    build_id: str
    runner_os: str
    runner_version: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    started_at: datetime
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class TestResponse(BaseModel):
    id: str
    repository_id: str
    name: str
    suite_name: Optional[str]
    file_path: str
    line_number: Optional[int]
    flakiness_score: float
    failure_rate: float
    run_count: int
    model_config = ConfigDict(from_attributes=True)

