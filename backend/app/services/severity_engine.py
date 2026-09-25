from backend.app.models.base import FailureClassification, SeverityLevel

class SeverityEngine:
    """
    Evaluates failure impact independently of flakiness or classification confidence.
    Follows Section 6 of specification: Severity is impact *if* real.
    """

    CRITICAL_MODULES = {"payment", "auth", "billing", "security", "checkout", "login"}

    def calculate_severity(
        self,
        classification: FailureClassification,
        branch: str,
        test_file_path: str,
        regression_prob: float,
        environment: str = "production"
    ) -> SeverityLevel:
        is_main = branch.lower() in {"main", "master", "release", "prod"}
        is_critical_path = any(mod in test_file_path.lower() for mod in self.CRITICAL_MODULES)

        # 1. Critical cases:
        # High regression probability on main/release in critical modules
        if is_main and is_critical_path and regression_prob >= 0.7:
            return SeverityLevel.CRITICAL
        if is_main and classification == FailureClassification.INFRASTRUCTURE and environment == "production":
            return SeverityLevel.CRITICAL

        # 2. High cases:
        # Genuine regression on main branch or build failure blocking main
        if is_main and (classification in [FailureClassification.REGRESSION, FailureClassification.BUILD_FAILURE]):
            return SeverityLevel.HIGH
        if is_critical_path and regression_prob >= 0.6:
            return SeverityLevel.HIGH

        # 3. Medium cases:
        # Regressions on feature branches or dependency / network blocking a PR
        if classification == FailureClassification.REGRESSION:
            return SeverityLevel.MEDIUM
        if classification in [FailureClassification.DEPENDENCY, FailureClassification.NETWORK]:
            return SeverityLevel.MEDIUM

        # 4. Low cases:
        # Flaky tests or minor test-data inconsistencies
        if classification == FailureClassification.FLAKY_TEST:
            return SeverityLevel.LOW
        if classification == FailureClassification.TEST_DATA:
            return SeverityLevel.LOW

        # Default normal
        return SeverityLevel.NORMAL

severity_engine = SeverityEngine()
