from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.database import get_db
from backend.app.models.pipeline import Repository, Pipeline, Build, TestRun, Test
from backend.app.schemas.pipeline import (
    RepositoryResponse,
    PipelineResponse,
    BuildResponse,
    TestRunResponse,
    TestResponse
)

router = APIRouter(tags=["Pipelines & Builds"])

@router.get("/repositories", response_model=List[RepositoryResponse])
def get_repositories(db: Session = Depends(get_db)):
    return db.query(Repository).all()

@router.get("/pipelines", response_model=List[PipelineResponse])
def get_pipelines(repo_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Pipeline)
    if repo_id:
        q = q.filter_by(repository_id=repo_id)
    return q.all()

@router.get("/pipelines/{pipeline_id}/builds", response_model=List[BuildResponse])
def get_pipeline_builds(
    pipeline_id: str,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return (
        db.query(Build)
        .filter_by(pipeline_id=pipeline_id)
        .order_by(desc(Build.build_number))
        .limit(limit)
        .all()
    )

@router.get("/builds", response_model=List[BuildResponse])
def get_all_builds(
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return db.query(Build).order_by(desc(Build.started_at)).limit(limit).all()

@router.get("/builds/{build_id}", response_model=BuildResponse)
def get_build_detail(build_id: str, db: Session = Depends(get_db)):
    build = db.query(Build).filter_by(id=build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build

@router.get("/builds/{build_id}/test-runs", response_model=List[TestRunResponse])
def get_build_test_runs(build_id: str, db: Session = Depends(get_db)):
    return db.query(TestRun).filter_by(build_id=build_id).all()

@router.get("/tests", response_model=List[TestResponse])
def get_tests(
    min_flakiness: float = 0.0,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return (
        db.query(Test)
        .filter(Test.flakiness_score >= min_flakiness)
        .order_by(desc(Test.flakiness_score))
        .limit(limit)
        .all()
    )
