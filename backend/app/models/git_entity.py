import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class Commit(Base):
    __tablename__ = "commits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    sha = Column(String(64), unique=True, index=True, nullable=False)
    author_name = Column(String(128), nullable=False)
    author_email = Column(String(255), index=True, nullable=False)
    message = Column(Text, nullable=False)
    branch = Column(String(128), default="main")
    committed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="commits")
    changed_files = relationship("ChangedFile", back_populates="commit", cascade="all, delete-orphan")

class ChangedFile(Base):
    __tablename__ = "changed_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    commit_id = Column(String(36), ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(255), index=True, nullable=False)
    change_type = Column(String(32), default="modified")  # added, modified, deleted
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    patch_summary = Column(Text, nullable=True)

    # Relationships
    commit = relationship("Commit", back_populates="changed_files")

class Owner(Base):
    __tablename__ = "owners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    team_name = Column(String(128), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    components = relationship("Component", back_populates="lead_owner")

class Component(Base):
    __tablename__ = "components"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    lead_owner_id = Column(String(36), ForeignKey("owners.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    lead_owner = relationship("Owner", back_populates="components")

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id = Column(String(64), index=True, nullable=False)
    environment = Column(String(64), default="production", index=True, nullable=False)
    commit_sha = Column(String(64), index=True, nullable=False)
    status = Column(String(32), default="SUCCESS")  # SUCCESS, FAILED, ROLLING_BACK
    deployed_by = Column(String(128), default="ci-cd-bot")
    deployed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
