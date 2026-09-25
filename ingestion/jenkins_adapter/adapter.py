import logging
from typing import Dict, Any, List, Optional
from ingestion.base_adapter import CIAdapter

logger = logging.getLogger(__name__)

class JenkinsAdapter(CIAdapter):
    """
    Jenkins CI adapter stub implementing the CIAdapter interface.
    Ready for connection to a Jenkins server via python-jenkins or REST API.
    """

    def __init__(self, base_url: str = "http://localhost:8080", username: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url
        self.username = username
        self.token = token

    def fetch_workflow_run(self, run_id: str) -> Dict[str, Any]:
        logger.info(f"JenkinsAdapter: fetch_workflow_run called for {run_id}")
        return {
            "id": run_id,
            "provider": "jenkins",
            "status": "completed",
            "result": "FAILURE",
            "url": f"{self.base_url}/job/demo-job/{run_id}"
        }

    def fetch_run_jobs(self, run_id: str) -> List[Dict[str, Any]]:
        logger.info(f"JenkinsAdapter: fetch_run_jobs called for {run_id}")
        return [{
            "id": f"stage-build-{run_id}",
            "name": "Build & Test Stage",
            "status": "FAILED"
        }]

    def fetch_job_logs(self, job_id: str) -> str:
        logger.info(f"JenkinsAdapter: fetch_job_logs called for {job_id}")
        return "Started by user JenkinsAdmin\n[ERROR] Test suite failed: connection refused to redis-service\n"

    def fetch_commit_details(self, commit_sha: str) -> Dict[str, Any]:
        logger.info(f"JenkinsAdapter: fetch_commit_details called for {commit_sha}")
        return {
            "sha": commit_sha,
            "author": "jenkins-committer",
            "message": "Jenkins trigger commit",
            "files": []
        }

    def trigger_rerun(self, run_id: str) -> Dict[str, Any]:
        logger.info(f"JenkinsAdapter: trigger_rerun called for {run_id}")
        return {"status": "accepted", "provider": "jenkins", "message": f"Queued Jenkins build for {run_id}"}
