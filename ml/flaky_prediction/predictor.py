import os
import joblib
import logging
from typing import Dict, Any, List, Tuple
import numpy as np
import lightgbm as lgb
from ml.feature_engineering.extractor import extract_flaky_test_features

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models_store", "flaky_predictor.joblib")

class FlakyPredictor:
    def __init__(self):
        self.model = None
        self.feature_names = []
        self._load_or_train()

    def _train_default_model(self):
        logger.info("Training initial baseline flaky test predictor...")

        # Synthetic benchmark training points: [flip_rate, failure_rate, duration_variance, total_runs, recent_flips, test_age_days] -> is_flaky (0 or 1)
        samples = [
            # High flip rate & variance = flaky
            ([0.65, 0.45, 12.5, 80.0, 0.6, 90.0], 1),
            ([0.50, 0.30, 8.2, 50.0, 0.5, 45.0], 1),
            ([0.70, 0.50, 15.0, 120.0, 0.7, 180.0], 1),
            ([0.40, 0.25, 6.0, 40.0, 0.4, 30.0], 1),
            ([0.80, 0.40, 20.0, 60.0, 0.8, 60.0], 1),

            # Stable passing tests = not flaky
            ([0.00, 0.00, 0.01, 100.0, 0.0, 120.0], 0),
            ([0.01, 0.01, 0.05, 90.0, 0.0, 100.0], 0),
            ([0.00, 0.00, 0.02, 50.0, 0.0, 40.0], 0),

            # Genuine regression (was passing continuously, now failed and stays failed) = not flaky
            ([0.02, 0.10, 0.04, 50.0, 0.1, 80.0], 0),
            ([0.05, 0.20, 0.10, 40.0, 0.0, 60.0], 0),
            ([0.01, 0.05, 0.02, 100.0, 0.0, 150.0], 0),
        ]

        self.feature_names = ["flip_rate", "failure_rate", "duration_variance", "total_runs", "recent_flips", "test_age_days"]
        X = np.array([s[0] for s in samples])
        y = np.array([s[1] for s in samples])

        clf = lgb.LGBMClassifier(
            n_estimators=25,
            learning_rate=0.1,
            random_state=42,
            verbose=-1,
            min_child_samples=1
        )
        clf.fit(X, y)
        self.model = clf

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump({"model": self.model, "feature_names": self.feature_names}, MODEL_PATH)
        logger.info(f"Flaky predictor model saved to {MODEL_PATH}")

    def _load_or_train(self):
        if os.path.exists(MODEL_PATH):
            try:
                bundle = joblib.load(MODEL_PATH)
                self.model = bundle["model"]
                self.feature_names = bundle["feature_names"]
                logger.info("Loaded pre-trained flaky predictor.")
                return
            except Exception as e:
                logger.warning(f"Error loading flaky predictor ({e}). Re-training.")
        self._train_default_model()

    def predict_flakiness(
        self,
        run_history: List[Dict[str, Any]],
        test_age_days: float = 30.0
    ) -> Tuple[bool, float, Dict[str, float]]:
        """
        Returns (predicted_is_flaky, flaky_probability, features_dict)
        """
        feats = extract_flaky_test_features(run_history, test_age_days)
        row = np.array([[feats[k] for k in self.feature_names]])

        try:
            probs = self.model.predict_proba(row)[0]
            flaky_prob = float(probs[1])
            is_flaky = bool(flaky_prob >= 0.5)
            return is_flaky, flaky_prob, feats
        except Exception as e:
            logger.error(f"Flaky prediction error: {e}")
            # Fallback heuristic based on flip_rate
            flip = feats.get("flip_rate", 0.0)
            return bool(flip > 0.3), float(min(1.0, flip * 1.5)), feats

flaky_predictor = FlakyPredictor()
