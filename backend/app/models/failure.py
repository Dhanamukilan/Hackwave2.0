import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum as SAEnum, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import FailureClassification, SeverityLevel

class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hash_value = Column(String(64), unique=True, index=True, nullable=False)
    error_type = Column(String(128), index=True, nullable=False)
    normalized_message = Column(Text, nullable=False)
    location = Column(String(255), index=True, nullable=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    failures = relationship("Failure", back_populates="fingerprint")

class Failure(Base):
    __tablename__ = "failures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_run_id = Column(String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False)
    test_id = Column(String(36), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    fingerprint_id = Column(String(36), ForeignKey("fingerprints.id"), nullable=True)

    error_type = Column(String(128), index=True, nullable=False)
    raw_message = Column(Text, nullable=False)
    normalized_message = Column(Text, nullable=False)
    raw_stack_trace = Column(Text, nullable=True)
    normalized_stack_trace = Column(Text, nullable=True)

    # Core scores (strictly separated per Section 6 of spec)
    classification = Column(SAEnum(FailureClassification), default=FailureClassification.UNKNOWN, nullable=False)
    classification_confidence = Column(Float, default=0.5)
    flakiness_score = Column(Float, default=0.0)      # Flakiness probability (0.0 - 1.0)
    regression_prob = Column(Float, default=0.0)      # Regression probability (0.0 - 1.0)
    severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.NORMAL, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    test_run = relationship("TestRun", back_populates="failures")
    test = relationship("Test", back_populates="failures")
    fingerprint = relationship("Fingerprint", back_populates="failures")
    investigations = relationship("Investigation", back_populates="failure", cascade="all, delete-orphan")

    @property
    def ci_provider(self) -> str:
        if self.test_run and self.test_run.build and self.test_run.build.pipeline:
            return self.test_run.build.pipeline.provider or "github_actions"
        return "github_actions"

    @property
    def pipeline_name(self) -> str:
        if self.test_run and self.test_run.build and self.test_run.build.pipeline:
            return self.test_run.build.pipeline.name or "CI"
        return "CI"

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(String(36), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    build_id = Column(String(36), ForeignKey("builds.id", ondelete="CASCADE"), nullable=False)
    model_name = Column(String(64), nullable=False)
    model_version = Column(String(32), default="v1.0")
    predicted_is_flaky = Column(Boolean, default=False, nullable=False)
    flaky_probability = Column(Float, default=0.0, nullable=False)
    features_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    test = relationship("Test", back_populates="predictions")
    build = relationship("Build", back_populates="predictions")
