from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from backend.app.models.base import InvestigationStatus, RCAConfidence, RemediationStatus

class RemediationResponse(BaseModel):
    id: str
    investigation_id: str
    proposed_action: str
    action_type: str
    diff_or_script: Optional[str]
    status: RemediationStatus
    approved_by_user_id: Optional[str]
    approved_at: Optional[datetime]
    execution_result: Optional[Dict[str, Any]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class InvestigationResponse(BaseModel):
    id: str
    failure_id: str
    status: InvestigationStatus
    rca_summary: Optional[str]
    confidence: RCAConfidence
    hypotheses_evaluated: Optional[List[Dict[str, Any]]]
    evidence_bundle: Optional[Dict[str, Any]]
    assigned_to_user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    remediations: List[RemediationResponse] = []
    model_config = ConfigDict(from_attributes=True)

class FeedbackCreate(BaseModel):
    investigation_id: str
    is_rca_correct: bool
    actual_classification: Optional[str] = None
    comments: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: str
    investigation_id: str
    user_id: Optional[str]
    is_rca_correct: bool
    actual_classification: Optional[str]
    comments: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

