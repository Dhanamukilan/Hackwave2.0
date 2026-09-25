import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.models.base import BuildStatus

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), index=True, nullable=False)
    full_name = Column(String(255), unique=True, index=True, nullable=False)
    default_branch = Column(String(64), default="main", nullable=False)
    clone_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pipelines = relationship("Pipeline", back_populates="repository", cascade="all, delete-orphan")
    tests = relationship("Test", back_populates="repository", cascade="all, delete-orphan")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")

class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(128), nullable=False)
    workflow_path = Column(String(255), nullable=False)  # e.g. .github/workflows/ci.yml
    provider = Column(String(32), default="github_actions", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="pipelines")
    builds = relationship("Build", back_populates="pipeline", cascade="all, delete-orphan")

class Build(Base):
    __tablename__ = "builds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_id = Column(String(36), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    commit_sha = Column(String(64), index=True, nullable=False)
    branch = Column(String(128), index=True, nullable=False)
    build_number = Column(Integer, nullable=False)
    status = Column(SAEnum(BuildStatus), default=BuildStatus.QUEUED, nullable=False)
    trigger = Column(String(64), default="push")  # push, pull_request, workflow_dispatch
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="builds")
    test_runs = relationship("TestRun", back_populates="build", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="build", cascade="all, delete-orphan")

class TestRun(Base):
    __tablename__ = "test_runs"
    __test__ = False

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    build_id = Column(String(36), ForeignKey("builds.id", ondelete="CASCADE"), nullable=False)
    runner_os = Column(String(64), default="ubuntu-latest")
    runner_version = Column(String(64), default="22.04")
    total_tests = Column(Integer, default=0)
    passed_tests = Column(Integer, default=0)
    failed_tests = Column(Integer, default=0)
    skipped_tests = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    build = relationship("Build", back_populates="test_runs")
    failures = relationship("Failure", back_populates="test_run", cascade="all, delete-orphan")

class Test(Base):
    __tablename__ = "tests"
    __test__ = False

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), index=True, nullable=False)
    suite_name = Column(String(255), index=True, nullable=True)
    file_path = Column(String(255), index=True, nullable=False)
    line_number = Column(Integer, nullable=True)
    flakiness_score = Column(Float, default=0.0)
    failure_rate = Column(Float, default=0.0)
    run_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="tests")
    failures = relationship("Failure", back_populates="test", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="test", cascade="all, delete-orphan")
