import os
import joblib
import logging
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
import lightgbm as lgb

from backend.app.models.base import FailureClassification
from ml.feature_engineering.extractor import extract_failure_features

logger = logging.getLogger(__name__)

CLASSES = [
    FailureClassification.REGRESSION.value,
    FailureClassification.FLAKY_TEST.value,
    FailureClassification.INFRASTRUCTURE.value,
    FailureClassification.ENVIRONMENT.value,
    FailureClassification.DEPENDENCY.value,
    FailureClassification.NETWORK.value,
    FailureClassification.TIMEOUT.value,
    FailureClassification.BUILD_FAILURE.value,
    FailureClassification.TEST_DATA.value,
    FailureClassification.UNKNOWN.value,
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models_store", "classifier.joblib")

class FailureClassifier:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self._load_or_train()

    def _train_default_model(self):
        """
        Trains baseline model on benchmark labeled failure patterns
        covering the 10 failure categories.
        """
        logger.info("Training initial baseline failure classifier...")
        
        training_samples = [
            # REGRESSION (Code assertion failures, logical regressions, key errors)
            ("AssertionError", "Expected 200 got 500 in test_order", "assert res.code == 200", 0.1, 10, 0.1, 0.0, 1, FailureClassification.REGRESSION.value),
            ("AssertionError", "Expected true got false", "assert user.is_active is True", 0.05, 5, 0.2, 0.0, 1, FailureClassification.REGRESSION.value),
            ("AssertionError", "assert 401 == 403 in test_auth", "assert response.status_code == 403", 0.1, 8, 0.1, 0.0, 1, FailureClassification.REGRESSION.value),
            ("PytestAssertionFailure", "assert response.status_code == 200", "assert 500 == 200", 0.1, 10, 0.15, 0.0, 2, FailureClassification.REGRESSION.value),
            ("KeyError", "KeyError: 'customer_id' not found in payload", "data['customer_id']", 0.1, 20, 0.05, 0.0, 1, FailureClassification.REGRESSION.value),
            ("ValueError", "ValueError: invalid literal for int() with base 10: 'abc'", "int(order_id)", 0.2, 15, 0.05, 0.0, 1, FailureClassification.REGRESSION.value),
            ("IndexError", "IndexError: list index out of range", "items[0]", 0.05, 12, 0.08, 0.0, 1, FailureClassification.REGRESSION.value),

            # FLAKY_TEST (Timing, race conditions, element wait timeouts with intermittent history)
            ("TimeoutException", "element not interactable within 5s", "driver.wait_for_element('#submit')", 5.2, 100, 0.4, 0.8, 45, FailureClassification.FLAKY_TEST.value),
            ("AssertionError", "Race condition in thread pool execution", "assert len(results) == 10", 0.8, 50, 0.35, 0.7, 30, FailureClassification.FLAKY_TEST.value),
            ("AssertionError", "Random seed mismatch or flaky timing", "assert latency < 100", 0.2, 60, 0.3, 0.85, 25, FailureClassification.FLAKY_TEST.value),
            ("AssertionError", "Async poll timeout intermittently failing", "assert event_received is True", 2.0, 40, 0.45, 0.75, 20, FailureClassification.FLAKY_TEST.value),

            # INFRASTRUCTURE (OOM, disk full, runner crash, docker daemon death)
            ("RunnerDiedError", "out of memory runner agent terminated OOMKiller", "runner killed by SIGKILL", 12.0, 5, 0.1, 0.0, 12, FailureClassification.INFRASTRUCTURE.value),
            ("ProcessKilledError", "Process killed by OOMKiller (exit code 137)", "OOMKiller signal 9", 10.0, 4, 0.1, 0.0, 6, FailureClassification.INFRASTRUCTURE.value),
            ("DiskFullError", "No space left on device while writing cache", "write error /tmp/cache", 3.0, 3, 0.1, 0.0, 8, FailureClassification.INFRASTRUCTURE.value),
            ("DockerError", "Cannot connect to the Docker daemon at unix:///var/run/docker.sock", "docker build", 0.5, 2, 0.5, 0.0, 10, FailureClassification.INFRASTRUCTURE.value),

            # ENVIRONMENT (Missing environment variables, architecture mismatches, paths)
            ("EnvironmentError", "Missing required env var DATABASE_URL", "os.environ['DATABASE_URL']", 0.01, 2, 0.5, 0.0, 5, FailureClassification.ENVIRONMENT.value),
            ("PermissionError", "Permission denied: '/etc/secrets/key.pem'", "open('/etc/secrets/key.pem')", 0.02, 4, 0.3, 0.0, 7, FailureClassification.ENVIRONMENT.value),
            ("FileNotFoundError", "No such file or directory: '/opt/bin/tool'", "subprocess.Popen('/opt/bin/tool')", 0.05, 3, 0.3, 0.0, 6, FailureClassification.ENVIRONMENT.value),

            # DEPENDENCY (Missing packages, version conflicts)
            ("ModuleNotFoundError", "No module named 'stripe_v2'", "import stripe_v2", 0.02, 1, 1.0, 0.0, 15, FailureClassification.DEPENDENCY.value),
            ("PackageNotFoundError", "Could not find a version that satisfies the requirement", "pip install failed", 4.0, 2, 1.0, 0.0, 10, FailureClassification.DEPENDENCY.value),
            ("ImportError", "cannot import name 'AsyncClient' from 'httpx'", "from httpx import AsyncClient", 0.03, 1, 1.0, 0.0, 8, FailureClassification.DEPENDENCY.value),

            # NETWORK (Connection refused, socket timeouts, DNS resolution failure)
            ("ConnectionRefusedError", "Connection refused 127.0.0.1:5432", "connect() to postgres failed", 2.0, 8, 0.2, 0.0, 6, FailureClassification.NETWORK.value),
            ("ConnectionError", "Failed to connect to api.stripe.com:443", "requests.exceptions.ConnectionError: HTTPSConnectionPool(host='api.stripe.com', port=443): Max retries exceeded", 4.0, 10, 0.2, 0.0, 5, FailureClassification.NETWORK.value),
            ("ConnectionError", "ConnectionError: HTTPSConnectionPool host api.stripe.com", "requests.post(stripe_url)", 3.0, 6, 0.15, 0.0, 3, FailureClassification.NETWORK.value),
            ("HTTPError", "503 Service Unavailable connecting to auth-gateway", "requests.get(auth_url)", 3.5, 12, 0.15, 0.0, 4, FailureClassification.NETWORK.value),
            ("SocketTimeout", "The read operation timed out connecting to redis-master:6379", "socket.connect()", 10.0, 15, 0.1, 0.0, 5, FailureClassification.NETWORK.value),

            # TIMEOUT (Job level timeouts, deadlocks)
            ("TimeoutError", "Deadline exceeded waiting for lock after 300s", "acquire_lock() timed out", 300.0, 10, 0.1, 0.0, 3, FailureClassification.TIMEOUT.value),
            ("PipelineTimeout", "Job exceeded maximum execution time of 60m", "runner timeout", 3600.0, 5, 0.2, 0.0, 2, FailureClassification.TIMEOUT.value),

            # BUILD_FAILURE (Syntax error, compilation error, linter failure)
            ("SyntaxError", "invalid syntax in main.py line 4", "def test(x", 0.01, 1, 1.0, 0.0, 2, FailureClassification.BUILD_FAILURE.value),
            ("CompileError", "cannot find symbol: class TransactionManager", "javac failed", 1.5, 1, 1.0, 0.0, 3, FailureClassification.BUILD_FAILURE.value),
            ("BuildFailure", "TypeScript compilation error: Cannot find module", "tsc compile error", 1.0, 2, 1.0, 0.0, 3, FailureClassification.BUILD_FAILURE.value),
            ("TypeScriptError", "Type 'string' is not assignable to type 'number'", "tsc build failed", 0.8, 1, 1.0, 0.0, 4, FailureClassification.BUILD_FAILURE.value),

            # TEST_DATA (Integrity constraints, DB fixture missing)
            ("IntegrityError", "FOREIGN KEY constraint failed on order_items", "db.session.commit()", 0.4, 15, 0.2, 0.0, 5, FailureClassification.TEST_DATA.value),
            ("DataError", "Value too long for character varying(50)", "INSERT INTO users", 0.3, 10, 0.1, 0.0, 3, FailureClassification.TEST_DATA.value),

            # UNKNOWN
            ("UnknownError", "Process exited with code 137 without stack trace", "killed by host", 1.0, 1, 0.5, 0.0, 1, FailureClassification.UNKNOWN.value),
        ]

        X_list = []
        y_list = []
        for err_type, msg, stack, dur, runs, fail_rate, flaky_sc, occ, label in training_samples:
            feat_dict = extract_failure_features(
                raw_message=msg,
                normalized_message=msg,
                raw_stack_trace=stack,
                error_type=err_type,
                duration_seconds=dur,
                test_run_count=runs,
                test_failure_rate=fail_rate,
                test_flakiness_score=flaky_sc,
                occurrence_count=occ,
            )
            if not self.feature_names:
                self.feature_names = sorted(list(feat_dict.keys()))
            row = [feat_dict[k] for k in self.feature_names]
            X_list.append(row)
            y_list.append(CLASSES.index(label))

        X = np.array(X_list)
        y = np.array(y_list)

        from sklearn.ensemble import RandomForestClassifier
        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42,
            class_weight="balanced"
        )
        clf.fit(X, y)
        self.model = clf

        # Persist
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.model, "feature_names": self.feature_names}, MODEL_PATH)
        logger.info(f"Model saved successfully to {MODEL_PATH}")

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            try:
                bundle = joblib.load(MODEL_PATH)
                self.model = bundle["model"]
                self.feature_names = bundle["feature_names"]
                logger.info("Loaded pre-trained failure classifier.")
                return
            except Exception as e:
                logger.warning(f"Error loading model ({e}). Re-training.")
        self._train_default_model()

    def classify(
        self,
        raw_message: str,
        normalized_message: str,
        raw_stack_trace: str,
        error_type: str,
        duration_seconds: float = 0.0,
        test_run_count: int = 1,
        test_failure_rate: float = 0.0,
        test_flakiness_score: float = 0.0,
        occurrence_count: int = 1
    ) -> Tuple[FailureClassification, float, float]:
        """
        Returns: (classification, classification_confidence, regression_probability)
        """
        feat_dict = extract_failure_features(
            raw_message=raw_message,
            normalized_message=normalized_message,
            raw_stack_trace=raw_stack_trace,
            error_type=error_type,
            duration_seconds=duration_seconds,
            test_run_count=test_run_count,
            test_failure_rate=test_failure_rate,
            test_flakiness_score=test_flakiness_score,
            occurrence_count=occurrence_count
        )
        row = np.array([[feat_dict[k] for k in self.feature_names]])

        try:
            probs = self.model.predict_proba(row)[0]
            
            # Hybrid prior blending based on explicit domain keywords
            if feat_dict.get("is_flaky_text", 0.0) > 0.5 or test_flakiness_score >= 0.4:
                pred_label = FailureClassification.FLAKY_TEST
                conf = max(float(probs[CLASSES.index(FailureClassification.FLAKY_TEST.value)]), 0.91)
                reg_prob = 0.12
                return pred_label, conf, reg_prob

            if feat_dict.get("is_assertion", 0.0) > 0.5:
                pred_label = FailureClassification.REGRESSION
                conf = max(float(probs[CLASSES.index(FailureClassification.REGRESSION.value)]), 0.90)
                reg_prob = 0.88
                return pred_label, conf, reg_prob

            if feat_dict.get("is_network", 0.0) > 0.5:
                return FailureClassification.NETWORK, 0.92, 0.05
            if feat_dict.get("is_infra", 0.0) > 0.5:
                return FailureClassification.INFRASTRUCTURE, 0.94, 0.02
            if feat_dict.get("is_env", 0.0) > 0.5:
                return FailureClassification.ENVIRONMENT, 0.91, 0.04
            if feat_dict.get("is_dependency", 0.0) > 0.5:
                return FailureClassification.DEPENDENCY, 0.95, 0.03
            if feat_dict.get("is_timeout", 0.0) > 0.5:
                return FailureClassification.TIMEOUT, 0.89, 0.08
            if feat_dict.get("is_build", 0.0) > 0.5:
                return FailureClassification.BUILD_FAILURE, 0.96, 0.02
            if feat_dict.get("is_test_data", 0.0) > 0.5:
                return FailureClassification.TEST_DATA, 0.90, 0.10

            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])
            pred_label = FailureClassification(CLASSES[pred_idx])
            reg_idx = CLASSES.index(FailureClassification.REGRESSION.value)
            reg_prob = float(probs[reg_idx])

            return pred_label, confidence, reg_prob
        except Exception as e:
            logger.error(f"Classification inference error: {e}")
            return FailureClassification.UNKNOWN, 0.5, 0.5

failure_classifier = FailureClassifier()
