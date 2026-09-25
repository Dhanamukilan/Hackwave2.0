import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SAEnum, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import InvestigationStatus, RCAConfidence, RemediationStatus

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    failure_id = Column(String(36), ForeignKey("failures.id", ondelete="CASCADE"), nullable=False)
    status = Column(SAEnum(InvestigationStatus), default=InvestigationStatus.PENDING, nullable=False)
    rca_summary = Column(Text, nullable=True)
    confidence = Column(SAEnum(RCAConfidence), default=RCAConfidence.MEDIUM, nullable=False)
    hypotheses_evaluated = Column(JSON, nullable=True)  # Matrix of H1..H7 evaluation with evidence_ids
    evidence_bundle = Column(JSON, nullable=True)        # Structured tool-collected evidence items
    assigned_to_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    failure = relationship("Failure", back_populates="investigations")
    assignee = relationship("User", back_populates="assigned_investigations")
    remediations = relationship("Remediation", back_populates="investigation", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="investigation", cascade="all, delete-orphan")

class Remediation(Base):
    __tablename__ = "remediations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    proposed_action = Column(Text, nullable=False)
    action_type = Column(String(64), default="CODE_FIX")  # CODE_FIX, RETRY_PIPELINE, QUARANTINE_TEST, CONFIG_UPDATE
    diff_or_script = Column(Text, nullable=True)
    status = Column(SAEnum(RemediationStatus), default=RemediationStatus.PENDING_APPROVAL, nullable=False)
    approved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    execution_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    investigation = relationship("Investigation", back_populates="remediations")
    approver = relationship("User", back_populates="remediations_approved")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    investigation_id = Column(String(36), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_rca_correct = Column(Boolean, nullable=False)
    actual_classification = Column(String(64), nullable=True)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    investigation = relationship("Investigation", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(128), index=True, nullable=False)
    resource_type = Column(String(64), index=True, nullable=False)
    resource_id = Column(String(64), index=True, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
