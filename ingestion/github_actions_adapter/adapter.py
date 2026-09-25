import io
import re
import zipfile
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.orm import Session

from ingestion.base_adapter import CIAdapter
from ingestion.log_normalizer.junit_parser import parse_junit_xml
from ingestion.log_normalizer.normalizer import extract_error_signature
from backend.app.core.config import settings
from backend.app.models import Commit, ChangedFile, Failure, Investigation
from backend.app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

class GitHubActionsAdapter(CIAdapter):
    """
    Real GitHub Actions API Adapter for pulling workflow runs, job logs, artifacts, and commits.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ):
        self.token = token or settings.GITHUB_TOKEN
        self.owner = owner or settings.GITHUB_REPO_OWNER or "Dhanamukilan"
        self.repo = repo or settings.GITHUB_REPO_NAME or "Hackwave2.0"
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def fetch_workflow_run(self, run_id: str) -> Dict[str, Any]:
        """Fetches workflow run metadata from GitHub Actions REST API."""
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
        """Fetches all jobs associated with a workflow run."""
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
        """Fetches console logs for a specific job."""
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

    def fetch_run_artifacts(self, run_id: str) -> List[Dict[str, Any]]:
        """Lists build artifacts produced by a workflow run."""
        url = f"{self.base_url}/actions/runs/{run_id}/artifacts"
        if not self.token:
            return []
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self.headers)
                res.raise_for_status()
                return res.json().get("artifacts", [])
        except Exception as e:
            logger.error(f"GitHub API error listing artifacts for run {run_id}: {e}")
            return []

    def download_and_extract_junit_artifact(self, run_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Attempts to find and download a test results artifact (e.g. 'test-results' or '*.xml'),
        extracting and parsing JUnit XML test case records.
        """
        if not self.token:
            return None

        artifacts = self.fetch_run_artifacts(run_id)
        if not artifacts:
            return None

        # Look for test results artifact
        target_art = None
        for art in artifacts:
            name = art.get("name", "").lower()
            if "test" in name or "junit" in name or "result" in name:
                target_art = art
                break
        if not target_art and artifacts:
            target_art = artifacts[0]

        if not target_art:
            return None

        download_url = target_art.get("archive_download_url")
        if not download_url:
            return None

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                res = client.get(download_url, headers=self.headers)
                res.raise_for_status()
                zip_bytes = io.BytesIO(res.content)
                with zipfile.ZipFile(zip_bytes, "r") as z:
                    for filename in z.namelist():
                        if filename.endswith(".xml"):
                            xml_content = z.read(filename).decode("utf-8", errors="replace")
                            parsed_cases = parse_junit_xml(xml_content)
                            if parsed_cases:
                                logger.info(f"Successfully extracted {len(parsed_cases)} test cases from artifact {filename}")
                                return parsed_cases
        except Exception as e:
            logger.warning(f"Could not download or extract JUnit artifact for run {run_id}: {e}")

        return None

    def parse_failures_from_logs(self, logs_text: str) -> List[Dict[str, Any]]:
        """
        Parses test failure entries directly from raw console logs when structured artifacts are absent.
        """
        cases = []
        # Pattern matching pytest failures: FAILED tests/file.py::test_name - ErrorType: message
        failed_pattern = re.compile(r"FAILED\s+([^\s:]+)::([^\s\-]+)\s*-\s*([^\n]+)")
        matches = list(failed_pattern.finditer(logs_text))

        if matches:
            for m in matches:
                file_path = m.group(1)
                test_name = m.group(2)
                raw_err = m.group(3).strip()

                sig = extract_error_signature(raw_err)
                error_info = {
                    "error_type": sig["error_type"],
                    "raw_message": raw_err,
                    "normalized_message": sig["normalized_message"],
                    "stack_trace": raw_err,
                    "normalized_stack_trace": sig["normalized_text"],
                    "fingerprint_hash": sig["fingerprint_hash"],
                    "location": file_path
                }
                cases.append({
                    "name": test_name,
                    "suite_name": file_path,
                    "file_path": file_path,
                    "status": "FAILED",
                    "duration_seconds": 0.5,
                    "error_info": error_info
                })
        else:
            # Fallback generic failure extractor if job failed
            if "FAIL" in logs_text or "Error" in logs_text or "Exception" in logs_text:
                sig = extract_error_signature(logs_text[-2000:])
                cases.append({
                    "name": "ci_pipeline_execution",
                    "suite_name": "build_pipeline",
                    "file_path": "ci.yml",
                    "status": "FAILED",
                    "duration_seconds": 1.0,
                    "error_info": {
                        "error_type": sig["error_type"],
                        "raw_message": sig["raw_message"],
                        "normalized_message": sig["normalized_message"],
                        "stack_trace": sig["normalized_text"],
                        "normalized_stack_trace": sig["normalized_text"],
                        "fingerprint_hash": sig["fingerprint_hash"],
                        "location": "ci.yml"
                    }
                })

        return cases

    def fetch_commit_details(self, commit_sha: str) -> Dict[str, Any]:
        """Fetches commit metadata, author details, and file diffs."""
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
        """Triggers a rerun of failed jobs for a workflow run."""
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

    def ingest_workflow_run(
        self,
        db: Session,
        run_id: str,
        commit_sha: Optional[str] = None,
        branch: Optional[str] = None,
        repo_name: Optional[str] = None,
        workflow_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete end-to-end ingestion orchestrator for a GitHub Actions workflow run:
        1. Fetches run metadata from GitHub API if needed.
        2. Fetches commit details & changed files, persisting Commit & ChangedFile entities.
        3. Pulls JUnit XML artifacts (or falls back to console log parsing).
        4. Ingests records via IngestionService (idempotent).
        5. Automatically launches TriageOrchestrator for detected failures.
        """
        repo_name = repo_name or self.repo
        workflow_name = workflow_name or "CI"

        # 1. Fetch run details if commit_sha missing
        if not commit_sha or not branch:
            run_meta = self.fetch_workflow_run(run_id)
            commit_sha = commit_sha or run_meta.get("head_sha", "HEAD")
            branch = branch or run_meta.get("head_branch", "main")
            workflow_name = workflow_name or run_meta.get("name", "CI")

        # 2. Fetch and persist commit details
        commit_data = self.fetch_commit_details(commit_sha)
        existing_commit = db.query(Commit).filter_by(sha=commit_sha).first()
        if not existing_commit and "commit" in commit_data:
            c_info = commit_data.get("commit", {})
            author_info = c_info.get("author", {})
            new_commit = Commit(
                sha=commit_sha,
                author_name=author_info.get("name", "Unknown"),
                author_email=author_info.get("email", "unknown@example.com"),
                message=c_info.get("message", "CI commit"),
                branch=branch or "main",
                committed_at=datetime.now(timezone.utc)
            )
            db.add(new_commit)
            db.flush()

            for f in commit_data.get("files", []):
                changed = ChangedFile(
                    commit_sha=commit_sha,
                    file_path=f.get("filename", "unknown"),
                    change_type=f.get("status", "modified"),
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                    patch=f.get("patch", "")
                )
                db.add(changed)
            db.commit()

        # 3. Pull JUnit artifact or fallback to logs
        test_cases = self.download_and_extract_junit_artifact(run_id)
        if not test_cases:
            jobs = self.fetch_run_jobs(run_id)
            combined_logs = ""
            for j in jobs:
                jid = str(j.get("id"))
                combined_logs += self.fetch_job_logs(jid) + "\n"
            test_cases = self.parse_failures_from_logs(combined_logs)

        # 4. Ingest via IngestionService
        ingest_svc = IngestionService(db)
        ingest_result = ingest_svc.ingest_test_execution_record(
            repo_name=repo_name,
            pipeline_name=workflow_name,
            commit_sha=commit_sha,
            branch=branch,
            test_case_records=test_cases,
            runner_os="ubuntu-latest",
            runner_version="22.04"
        )

        # 5. Automatically trigger autonomous RCA investigations for ingested failures
        from agents.orchestrator.orchestrator import TriageOrchestrator
        investigation_results = []
        triage_orch = TriageOrchestrator(db)
        for failure_id in ingest_result.get("failures_created", []):
            existing_inv = db.query(Investigation).filter_by(failure_id=failure_id).first()
            if not existing_inv:
                try:
                    inv = triage_orch.run_investigation(failure_id)
                    investigation_results.append({
                        "investigation_id": inv.id,
                        "failure_id": failure_id,
                        "status": inv.status.value,
                        "confidence": inv.confidence.value,
                        "summary": inv.rca_summary
                    })
                except Exception as e:
                    logger.error(f"Error executing triage investigation for {failure_id}: {e}")

        return {
            "ingest_result": ingest_result,
            "investigations": investigation_results
        }

github_actions_adapter = GitHubActionsAdapter()
