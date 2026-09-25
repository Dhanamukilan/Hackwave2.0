from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class CIAdapter(ABC):
    """
    Abstract Base Class for CI/CD Provider Adapters (GitHub Actions, Jenkins, etc.)
    """

    @abstractmethod
    def fetch_workflow_run(self, run_id: str) -> Dict[str, Any]:
        """Fetch details of a pipeline / workflow run."""
        pass

    @abstractmethod
    def fetch_run_jobs(self, run_id: str) -> List[Dict[str, Any]]:
        """Fetch jobs/steps for a run."""
        pass

    @abstractmethod
    def fetch_job_logs(self, job_id: str) -> str:
        """Fetch raw console/step logs for a job."""
        pass

    @abstractmethod
    def fetch_commit_details(self, commit_sha: str) -> Dict[str, Any]:
        """Fetch commit message, author, changed files, and diff hunks."""
        pass

    @abstractmethod
    def trigger_rerun(self, run_id: str) -> Dict[str, Any]:
        """Trigger re-run of failed jobs or workflow."""
        pass
