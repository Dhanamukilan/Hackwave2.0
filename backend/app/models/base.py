import enum
from backend.app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"

class FailureClassification(str, enum.Enum):
    REGRESSION = "REGRESSION"
    FLAKY_TEST = "FLAKY_TEST"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    ENVIRONMENT = "ENVIRONMENT"
    DEPENDENCY = "DEPENDENCY"
    NETWORK = "NETWORK"
    TIMEOUT = "TIMEOUT"
    BUILD_FAILURE = "BUILD_FAILURE"
    TEST_DATA = "TEST_DATA"
    UNKNOWN = "UNKNOWN"

class SeverityLevel(str, enum.Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RCAConfidence(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class InvestigationStatus(str, enum.Enum):
    PENDING = "PENDING"
    INVESTIGATING = "INVESTIGATING"
    RCA_READY = "RCA_READY"
    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class RemediationStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"

class BuildStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    CANCELLED = "CANCELLED"
