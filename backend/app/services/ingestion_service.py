import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.app.models import (
    Repository, Pipeline, Build, TestRun, Test,
    Fingerprint, Failure, BuildStatus, FailureClassification, SeverityLevel
)
from ingestion.log_normalizer.normalizer import extract_error_signature, generate_fingerprint
from database.vector_store.qdrant_client import vector_store
from ml.classification.classifier import failure_classifier
from ml.flaky_prediction.predictor import flaky_predictor
from backend.app.services.severity_engine import severity_engine

logger = logging.getLogger(__name__)

def generate_dense_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generates a deterministic normalized 384-dimensional dense vector representation
    from text tokens for semantic similarity search in Qdrant.
    """
    import numpy as np
    import hashlib

    # Compute a multi-hash dense projection vector
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    if not words:
        words = ["empty_log"]

    for i, word in enumerate(words):
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        slot = h % dim
        sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
        vec[slot] += sign * (1.0 / (1.0 + 0.1 * i))

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    def ingest_test_execution_record(
        self,
        repo_name: str,
        pipeline_name: str,
        commit_sha: str,
        branch: str,
        test_case_records: List[Dict[str, Any]],
        runner_os: str = "ubuntu-latest",
        runner_version: str = "22.04",
        provider: str = "github_actions"
    ) -> Dict[str, Any]:
        """
        Processes a full batch of executed test cases for a build run,
        registers repository, pipeline, build, test run, test records,
        and saves normalized failures + fingerprints + Qdrant vectors.
        """
        # 1. Repository
        repo = self.db.query(Repository).filter_by(name=repo_name).first()
        if not repo:
            repo = Repository(
                name=repo_name,
                full_name=f"org/{repo_name}",
                default_branch=branch or "main",
                clone_url=f"https://github.com/org/{repo_name}.git"
            )
            self.db.add(repo)
            self.db.flush()

        # 2. Pipeline
        pipeline = self.db.query(Pipeline).filter_by(repository_id=repo.id, name=pipeline_name).first()
        if not pipeline:
            pipeline = Pipeline(
                repository_id=repo.id,
                name=pipeline_name,
                workflow_path=f".github/workflows/{pipeline_name.lower().replace(' ', '_')}.yml" if provider == "github_actions" else f"Jenkinsfile/{pipeline_name}",
                provider=provider
            )
            self.db.add(pipeline)
            self.db.flush()

        # 3. Build (with Idempotency check)
        existing_build = (
            self.db.query(Build)
            .filter_by(pipeline_id=pipeline.id, commit_sha=commit_sha)
            .first()
        )
        if existing_build:
            logger.info(f"Idempotent skip: Build {existing_build.id} already exists for pipeline {pipeline.name} and commit {commit_sha}")
            existing_tr = self.db.query(TestRun).filter_by(build_id=existing_build.id).first()
            existing_failures = (
                self.db.query(Failure).filter_by(test_run_id=existing_tr.id).all()
                if existing_tr else []
            )
            return {
                "repository_id": repo.id,
                "pipeline_id": pipeline.id,
                "build_id": existing_build.id,
                "test_run_id": existing_tr.id if existing_tr else None,
                "failed_count": len(existing_failures),
                "failures_created": [f.id for f in existing_failures],
                "idempotent_duplicate": True
            }

        last_build = (
            self.db.query(Build)
            .filter_by(pipeline_id=pipeline.id)
            .order_by(Build.build_number.desc())
            .first()
        )
        build_number = (last_build.build_number + 1) if last_build else 1

        failed_count = sum(1 for t in test_case_records if t.get("status") == "FAILED")
        build_status = BuildStatus.FAILURE if failed_count > 0 else BuildStatus.SUCCESS

        build = Build(
            pipeline_id=pipeline.id,
            commit_sha=commit_sha,
            branch=branch,
            build_number=build_number,
            status=build_status,
            trigger="push",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=sum(t.get("duration_seconds", 0.0) for t in test_case_records)
        )
        self.db.add(build)
        self.db.flush()

        # 4. TestRun
        test_run = TestRun(
            build_id=build.id,
            runner_os=runner_os,
            runner_version=runner_version,
            total_tests=len(test_case_records),
            passed_tests=sum(1 for t in test_case_records if t.get("status") == "PASSED"),
            failed_tests=failed_count,
            skipped_tests=sum(1 for t in test_case_records if t.get("status") == "SKIPPED"),
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        self.db.add(test_run)
        self.db.flush()

        failures_created = []

        # 5. Process each test
        for tc in test_case_records:
            test_name = tc.get("name")
            file_path = tc.get("file_path", "test.py")

            test = (
                self.db.query(Test)
                .filter_by(repository_id=repo.id, name=test_name, file_path=file_path)
                .first()
            )
            if not test:
                test = Test(
                    repository_id=repo.id,
                    name=test_name,
                    suite_name=tc.get("suite_name"),
                    file_path=file_path,
                    line_number=tc.get("line_number"),
                    run_count=1,
                    failure_rate=1.0 if tc.get("status") == "FAILED" else 0.0,
                    flakiness_score=0.0
                )
                self.db.add(test)
                self.db.flush()
            else:
                test.run_count += 1
                if tc.get("status") == "FAILED":
                    test.failure_rate = (test.failure_rate * (test.run_count - 1) + 1.0) / test.run_count
                else:
                    test.failure_rate = (test.failure_rate * (test.run_count - 1)) / test.run_count

            # If failed, process failure and fingerprint
            if tc.get("status") == "FAILED" and tc.get("error_info"):
                err = tc["error_info"]
                error_type = err.get("error_type", "UnknownError")
                norm_msg = err.get("normalized_message", "")
                loc = err.get("location")
                fp_hash = err.get("fingerprint_hash") or generate_fingerprint(error_type, norm_msg, loc)

                fingerprint = self.db.query(Fingerprint).filter_by(hash_value=fp_hash).first()
                if not fingerprint:
                    fingerprint = Fingerprint(
                        hash_value=fp_hash,
                        error_type=error_type,
                        normalized_message=norm_msg,
                        location=loc,
                        occurrence_count=1,
                        first_seen_at=datetime.now(timezone.utc),
                        last_seen_at=datetime.now(timezone.utc)
                    )
                    self.db.add(fingerprint)
                    self.db.flush()
                else:
                    fingerprint.occurrence_count += 1
                    fingerprint.last_seen_at = datetime.now(timezone.utc)

                # ----- ML Inference: Classify this failure -----
                classification, cls_confidence, reg_prob = failure_classifier.classify(
                    raw_message=err.get("raw_message", ""),
                    normalized_message=norm_msg,
                    raw_stack_trace=err.get("stack_trace", ""),
                    error_type=error_type,
                    duration_seconds=float(tc.get("duration_seconds", 0.0)),
                    test_run_count=test.run_count,
                    test_failure_rate=test.failure_rate,
                    test_flakiness_score=test.flakiness_score,
                    occurrence_count=fingerprint.occurrence_count
                )
                logger.info(
                    f"Classified failure for {test_name}: {classification.value} "
                    f"(confidence={cls_confidence:.2f}, regression_prob={reg_prob:.2f})"
                )

                # ----- ML Inference: Flaky prediction -----
                # Build a minimal run history from existing failures for this test
                prior_failures = (
                    self.db.query(Failure)
                    .filter_by(test_id=test.id)
                    .order_by(Failure.created_at.asc())
                    .limit(50)
                    .all()
                )
                run_history = []
                for pf in prior_failures:
                    run_history.append({
                        "status": "FAILED",
                        "duration_seconds": 0.0,
                    })
                # Add passing runs to represent the full history
                passing_runs = max(0, test.run_count - len(prior_failures))
                for _ in range(passing_runs):
                    run_history.insert(0, {"status": "PASSED", "duration_seconds": 0.0})

                is_flaky, flaky_score, flaky_feats = flaky_predictor.predict_flakiness(
                    run_history=run_history,
                    test_age_days=30.0
                )
                logger.info(
                    f"Flaky prediction for {test_name}: is_flaky={is_flaky}, "
                    f"score={flaky_score:.3f}, features={flaky_feats}"
                )

                # Update test-level flakiness score
                test.flakiness_score = flaky_score

                # ----- Severity calculation -----
                branch_name = branch or "main"
                severity = severity_engine.calculate_severity(
                    classification=classification,
                    branch=branch_name,
                    test_file_path=file_path,
                    regression_prob=reg_prob
                )

                # Create Failure record with REAL model outputs
                failure = Failure(
                    test_run_id=test_run.id,
                    test_id=test.id,
                    fingerprint_id=fingerprint.id,
                    error_type=error_type,
                    raw_message=err.get("raw_message", ""),
                    normalized_message=norm_msg,
                    raw_stack_trace=err.get("stack_trace", ""),
                    normalized_stack_trace=err.get("normalized_stack_trace", ""),
                    classification=classification,
                    classification_confidence=cls_confidence,
                    flakiness_score=flaky_score,
                    regression_prob=reg_prob,
                    severity=severity,
                    created_at=datetime.now(timezone.utc)
                )
                self.db.add(failure)
                self.db.flush()

                # Insert vector into Qdrant
                searchable_text = f"{error_type} {norm_msg} {loc or ''}"
                emb = generate_dense_embedding(searchable_text)
                vector_store.insert_failure_embedding(
                    point_id=failure.id,
                    vector=emb,
                    payload={
                        "fingerprint_id": fingerprint.id,
                        "failure_id": failure.id,
                        "test_id": test.id,
                        "classification": failure.classification.value,
                        "created_at": failure.created_at.isoformat(),
                        "error_signature": searchable_text
                    }
                )

                failures_created.append(failure.id)

        self.db.commit()

        return {
            "repository_id": repo.id,
            "pipeline_id": pipeline.id,
            "build_id": build.id,
            "test_run_id": test_run.id,
            "failed_count": failed_count,
            "failures_created": failures_created
        }
