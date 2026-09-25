import logging
import httpx
from typing import Dict, Any, List, Optional
from ingestion.base_adapter import CIAdapter
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubActionsAdapter(CIAdapter):
    """
    Real GitHub Actions API Adapter for pulling workflow runs, job logs, and commits.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ):
        self.token = token or settings.GITHUB_TOKEN
        self.owner = owner or settings.GITHUB_REPO_OWNER or "demo-org"
        self.repo = repo or settings.GITHUB_REPO_NAME or "demo-repo"
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def fetch_workflow_run(self, run_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/actions/runs/{run_id}"
        if not self.token:
            logger.info("No GitHub token configured. Returning mock workflow run.")
            return {
                "id": run_id,
                "status": "completed",
                "conclusion": "failure",
                "head_sha": "a1b2c3d4e5f67890",
                "head_branch": "main",
                "event": "push",
                "html_url": f"https://github.com/{self.owner}/{self.repo}/actions/runs/{run_id}",
            }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                res.raise_for_status()
                return res.json()
        except Exception as e:
            logger.error(f"GitHub API error fetching run {run_id}: {e}")
            return {"id": run_id, "status": "unknown", "error": str(e)}

    def fetch_run_jobs(self, run_id: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/actions/runs/{run_id}/jobs"
        if not self.token:
            return [{
                "id": f"job-{run_id}-1",
                "name": "build-and-test",
                "status": "completed",
                "conclusion": "failure",
                "runner_name": "GitHub Actions Hosted (ubuntu-latest)",
            }]

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                res.raise_for_status()
                return res.json().get("jobs", [])
        except Exception as e:
            logger.error(f"GitHub API error fetching jobs for run {run_id}: {e}")
            return []

    def fetch_job_logs(self, job_id: str) -> str:
        url = f"{self.base_url}/actions/jobs/{job_id}/logs"
        if not self.token:
            return (
                "2026-09-24T20:10:00.0000000Z ##[section]Starting: Test execution\n"
                "FAILED tests/test_payment.py::test_process_charge - AssertionError: assert 500 == 200\n"
                "File \"backend/services/payment.py\", line 124, in process_charge\n"
                "raise ConnectionError(\"Failed to connect to gateway at 192.168.1.100:443 (timeout)\")\n"
            )

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                res = client.get(url, headers=self.headers)
                res.raise_for_status()
                return res.text
        except Exception as e:
            logger.error(f"GitHub API error fetching logs for job {job_id}: {e}")
            return f"Error fetching logs: {e}"

    def fetch_commit_details(self, commit_sha: str) -> Dict[str, Any]:
        url = f"{self.base_url}/commits/{commit_sha}"
        if not self.token:
            return {
                "sha": commit_sha,
                "commit": {
                    "author": {"name": "Demo Dev", "email": "dev@example.com"},
                    "message": "fix(payment): update timeout threshold and retry logic",
                },
                "files": [
                    {
                        "filename": "backend/services/payment.py",
                        "status": "modified",
                        "additions": 14,
                        "deletions": 5,
                        "patch": "@@ -120,5 +120,14 @@ def process_charge():\n- timeout = 5\n+ timeout = 30",
                    }
                ],
            }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                res.raise_for_status()
                return res.json()
        except Exception as e:
            logger.error(f"GitHub API error fetching commit {commit_sha}: {e}")
            return {"sha": commit_sha, "error": str(e)}

    def trigger_rerun(self, run_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/actions/runs/{run_id}/rerun-failed-jobs"
        if not self.token:
            logger.info(f"Simulating rerun of failed jobs for run {run_id}")
            return {"status": "accepted", "message": "Simulated re-run triggered successfully"}

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=self.headers)
                res.raise_for_status()
                return {"status": "success", "response": res.json()}
        except Exception as e:
            logger.error(f"GitHub API error triggering rerun for {run_id}: {e}")
            return {"status": "error", "message": str(e)}
