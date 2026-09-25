import pytest
from backend.app.models.base import FailureClassification
from ml.classification.classifier import failure_classifier
from ml.flaky_prediction.predictor import flaky_predictor
from ml.clustering.clusterer import failure_clusterer
from ml.evaluation.evaluator import evaluator
from backend.app.core.database import SessionLocal, init_db

def test_failure_classifier_regression():
    label, conf, reg_prob = failure_classifier.classify(
        raw_message="AssertionError: Expected 200 got 500",
        normalized_message="AssertionError: Expected 200 got 500",
        raw_stack_trace="File 'test_api.py', line 10, in test_endpoint\nassert res.status == 200",
        error_type="AssertionError"
    )
    assert label in [FailureClassification.REGRESSION, FailureClassification.FLAKY_TEST]
    assert conf >= 0.0
    assert reg_prob >= 0.0

def test_flaky_test_predictor():
    history = [
        {"status": "PASSED", "duration_seconds": 1.0},
        {"status": "FAILED", "duration_seconds": 5.0},
        {"status": "PASSED", "duration_seconds": 1.2},
        {"status": "FAILED", "duration_seconds": 6.1},
        {"status": "PASSED", "duration_seconds": 0.9},
    ]
    is_flaky, prob, feats = flaky_predictor.predict_flakiness(history)
    assert is_flaky is True
    assert prob >= 0.5
    assert feats["flip_rate"] > 0.5

def test_failure_clustering():
    vecs = [
        [0.1, 0.2, 0.3, 0.4] + [0.0] * 380,
        [0.12, 0.21, 0.31, 0.39] + [0.0] * 380,
        [-0.5, -0.4, -0.3, -0.2] + [0.0] * 380,
        [-0.51, -0.39, -0.32, -0.21] + [0.0] * 380,
    ]
    labels, score = failure_clusterer.cluster_embeddings(vecs, n_clusters=2)
    assert len(labels) == 4
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]

def test_cold_start_evaluation():
    init_db()
    db = SessionLocal()
    metrics = evaluator.get_evaluation_metrics(db)
    assert metrics["provenance_label"] == "[synthetic benchmark]"
    assert "classification_metrics" in metrics
    assert metrics["classification_metrics"]["f1_score"] > 0.8
    db.close()
