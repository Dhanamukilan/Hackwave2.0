from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from ml.classification.classifier import failure_classifier
from ml.flaky_prediction.predictor import flaky_predictor
from ml.evaluation.evaluator import evaluator

router = APIRouter(prefix="/ml", tags=["ML Intelligence & Evaluation"])

class ClassifyRequest(BaseModel):
    raw_message: str
    normalized_message: str
    raw_stack_trace: str = ""
    error_type: str = "UnknownError"
    duration_seconds: float = 0.0
    test_run_count: int = 1
    test_failure_rate: float = 0.0
    test_flakiness_score: float = 0.0
    occurrence_count: int = 1

class FlakyPredictRequest(BaseModel):
    run_history: List[Dict[str, Any]]
    test_age_days: float = 30.0

@router.get("/metrics")
def get_evaluation_metrics(db: Session = Depends(get_db)):
    """
    Returns model evaluation metrics following Section 8 cold-start rules.
    Tag: '[synthetic benchmark]' if real samples < MIN_REAL_SAMPLES, otherwise '[real data]'.
    """
    return evaluator.get_evaluation_metrics(db)

@router.post("/classify")
def classify_failure(req: ClassifyRequest):
    pred_label, conf, reg_prob = failure_classifier.classify(
        raw_message=req.raw_message,
        normalized_message=req.normalized_message,
        raw_stack_trace=req.raw_stack_trace,
        error_type=req.error_type,
        duration_seconds=req.duration_seconds,
        test_run_count=req.test_run_count,
        test_failure_rate=req.test_failure_rate,
        test_flakiness_score=req.test_flakiness_score,
        occurrence_count=req.occurrence_count
    )
    return {
        "classification": pred_label.value,
        "classification_confidence": round(conf, 3),
        "regression_probability": round(reg_prob, 3)
    }

@router.post("/predict-flaky")
def predict_flaky_test(req: FlakyPredictRequest):
    is_flaky, flaky_prob, feats = flaky_predictor.predict_flakiness(
        run_history=req.run_history,
        test_age_days=req.test_age_days
    )
    return {
        "is_flaky": is_flaky,
        "flaky_probability": round(flaky_prob, 3),
        "features": feats
    }
