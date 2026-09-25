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

        # Synthetic benchmark training points:
        # [flip_rate, failure_rate, duration_variance, total_runs, recent_flips, test_age_days] -> is_flaky (0 or 1)
        # 50 samples covering diverse feature distributions including edge cases
        samples = [
            # ── Clearly flaky: high flip rate, varied history ──
            ([0.65, 0.45, 12.5, 80.0, 0.6, 90.0], 1),
            ([0.50, 0.30, 8.2, 50.0, 0.5, 45.0], 1),
            ([0.70, 0.50, 15.0, 120.0, 0.7, 180.0], 1),
            ([0.40, 0.25, 6.0, 40.0, 0.4, 30.0], 1),
            ([0.80, 0.40, 20.0, 60.0, 0.8, 60.0], 1),
            ([0.55, 0.35, 3.0, 30.0, 0.55, 50.0], 1),
            ([0.45, 0.28, 1.5, 25.0, 0.45, 70.0], 1),
            ([0.60, 0.42, 0.5, 20.0, 0.6, 40.0], 1),
            ([0.35, 0.22, 0.0, 18.0, 0.35, 55.0], 1),
            ([0.90, 0.48, 0.0, 15.0, 0.85, 30.0], 1),
            # Flaky with zero duration variance (all same speed but alternating pass/fail)
            ([0.53, 0.50, 0.0, 20.0, 0.55, 90.0], 1),
            ([0.47, 0.45, 0.0, 22.0, 0.50, 60.0], 1),
            ([0.42, 0.38, 0.0, 16.0, 0.40, 100.0], 1),
            ([0.38, 0.35, 0.0, 30.0, 0.38, 45.0], 1),
            ([1.00, 0.50, 0.0, 12.0, 1.00, 30.0], 1),  # perfect alternation
            # Moderate flakiness
            ([0.30, 0.20, 2.0, 40.0, 0.30, 80.0], 1),
            ([0.33, 0.25, 0.1, 35.0, 0.33, 65.0], 1),
            ([0.28, 0.18, 0.0, 50.0, 0.28, 90.0], 1),

            # ── Clearly stable: no flips, all passing ──
            ([0.00, 0.00, 0.01, 100.0, 0.0, 120.0], 0),
            ([0.01, 0.01, 0.05, 90.0, 0.0, 100.0], 0),
            ([0.00, 0.00, 0.02, 50.0, 0.0, 40.0], 0),
            ([0.00, 0.00, 0.0, 20.0, 0.0, 90.0], 0),
            ([0.00, 0.00, 0.0, 30.0, 0.0, 60.0], 0),
            ([0.00, 0.00, 0.0, 15.0, 0.0, 30.0], 0),
            ([0.00, 0.00, 0.0, 10.0, 0.0, 45.0], 0),
            ([0.00, 0.00, 0.0, 50.0, 0.0, 200.0], 0),

            # ── Genuine regression: was passing, now consistently failing (NOT flaky) ──
            ([0.02, 0.10, 0.04, 50.0, 0.1, 80.0], 0),
            ([0.05, 0.20, 0.10, 40.0, 0.0, 60.0], 0),
            ([0.01, 0.05, 0.02, 100.0, 0.0, 150.0], 0),
            ([0.05, 0.25, 0.0, 20.0, 0.0, 80.0], 0),
            ([0.03, 0.15, 0.0, 30.0, 0.0, 50.0], 0),
            ([0.04, 0.30, 0.0, 18.0, 0.0, 45.0], 0),
            ([0.05, 0.40, 0.0, 15.0, 0.0, 60.0], 0),

            # ── Single old failure then stable (NOT flaky) ──
            ([0.05, 0.05, 0.0, 20.0, 0.0, 90.0], 0),
            ([0.03, 0.03, 0.0, 30.0, 0.0, 150.0], 0),
            ([0.07, 0.07, 0.0, 15.0, 0.0, 70.0], 0),

            # ── Low-run edge cases ──
            ([0.00, 0.00, 0.0, 5.0, 0.0, 10.0], 0),   # new test, all passes
            ([0.00, 1.00, 0.0, 1.0, 0.0, 5.0], 0),     # brand new, single fail (regression)
            ([0.00, 0.50, 0.0, 2.0, 0.0, 7.0], 0),     # 2 runs, 1 fail (not enough data = not flaky)
            ([1.00, 0.50, 0.0, 4.0, 1.00, 5.0], 1),    # 4 runs, alternating = flaky signal

            # ── Borderline cases (near decision boundary) ──
            ([0.20, 0.15, 0.5, 30.0, 0.20, 60.0], 0),  # occasional flip but low rate
            ([0.25, 0.18, 1.0, 25.0, 0.22, 50.0], 0),  # slightly more but still regression-like
            ([0.15, 0.10, 0.3, 40.0, 0.15, 80.0], 0),  # minor flips, mostly stable
        ]

        self.feature_names = ["flip_rate", "failure_rate", "duration_variance", "total_runs", "recent_flips", "test_age_days"]
        X = np.array([s[0] for s in samples])
        y = np.array([s[1] for s in samples])

        clf = lgb.LGBMClassifier(
            n_estimators=50,
            learning_rate=0.1,
            max_depth=4,
            random_state=42,
            verbose=-1,
            min_child_samples=2,
            num_leaves=8
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
