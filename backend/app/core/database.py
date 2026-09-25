import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    db_url = settings.get_database_url()
    try:
        # Try connecting with short timeout if postgres
        if "postgresql" in db_url:
            test_engine = create_engine(
                db_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
            with test_engine.connect() as conn:
                logger.info("Successfully connected to PostgreSQL.")
            return test_engine
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL ({e}). "
            f"Falling back to SQLite database at {settings.SQLITE_PATH} for seamless local development."
        )

    # SQLite fallback
    sqlite_url = f"sqlite:///{settings.SQLITE_PATH}"
    sqlite_engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )

    # Enable foreign keys for SQLite
    @event.listens_for(sqlite_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return sqlite_engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from backend.app.models import (
        User, Repository, Pipeline, Build, TestRun, Test,
        Fingerprint, Failure, Commit, ChangedFile, Component,
        Owner, Deployment, Prediction, Investigation, Remediation,
        Feedback, AuditLog
    )
    Base.metadata.create_all(bind=engine)

    # Safe migration check: add must_change_password if upgrading from earlier schema
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT must_change_password FROM users LIMIT 1"))
        except Exception:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"))
                conn.commit()
                logger.info("Migrated users table: added must_change_password column.")
            except Exception as migrate_err:
                logger.warning(f"Column migration notice: {migrate_err}")

    logger.info("Database schema initialized successfully.")
