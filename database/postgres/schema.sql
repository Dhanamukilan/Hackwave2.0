-- AG004 PostgreSQL Database Schema DDL

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users and RBAC
CREATE TYPE user_role AS ENUM ('ADMIN', 'INVESTIGATOR', 'DEVELOPER', 'VIEWER');
CREATE TYPE failure_classification AS ENUM (
    'REGRESSION', 'FLAKY_TEST', 'INFRASTRUCTURE', 'ENVIRONMENT',
    'DEPENDENCY', 'NETWORK', 'TIMEOUT', 'BUILD_FAILURE', 'TEST_DATA', 'UNKNOWN'
);
CREATE TYPE severity_level AS ENUM ('NORMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE rca_confidence AS ENUM ('LOW', 'MEDIUM', 'HIGH');
CREATE TYPE investigation_status AS ENUM ('PENDING', 'INVESTIGATING', 'RCA_READY', 'REMEDIATION_PROPOSED', 'RESOLVED', 'CLOSED');
CREATE TYPE remediation_status AS ENUM ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'EXECUTED');
CREATE TYPE build_status AS ENUM ('QUEUED', 'IN_PROGRESS', 'SUCCESS', 'FAILURE', 'CANCELLED');

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'DEVELOPER',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repositories (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    full_name VARCHAR(255) UNIQUE NOT NULL,
    default_branch VARCHAR(64) NOT NULL DEFAULT 'main',
    clone_url VARCHAR(255),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipelines (
    id VARCHAR(36) PRIMARY KEY,
    repository_id VARCHAR(36) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    workflow_path VARCHAR(255) NOT NULL,
    provider VARCHAR(32) NOT NULL DEFAULT 'github_actions',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS builds (
    id VARCHAR(36) PRIMARY KEY,
    pipeline_id VARCHAR(36) NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    commit_sha VARCHAR(64) NOT NULL,
    branch VARCHAR(128) NOT NULL,
    build_number INTEGER NOT NULL,
    status build_status NOT NULL DEFAULT 'QUEUED',
    trigger VARCHAR(64) DEFAULT 'push',
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    duration_seconds FLOAT DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS test_runs (
    id VARCHAR(36) PRIMARY KEY,
    build_id VARCHAR(36) NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    runner_os VARCHAR(64) DEFAULT 'ubuntu-latest',
    runner_version VARCHAR(64) DEFAULT '22.04',
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITHOUT TIME ZONE
);

CREATE TABLE IF NOT EXISTS tests (
    id VARCHAR(36) PRIMARY KEY,
    repository_id VARCHAR(36) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    suite_name VARCHAR(255),
    file_path VARCHAR(255) NOT NULL,
    line_number INTEGER,
    flakiness_score FLOAT DEFAULT 0.0,
    failure_rate FLOAT DEFAULT 0.0,
    run_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fingerprints (
    id VARCHAR(36) PRIMARY KEY,
    hash_value VARCHAR(64) UNIQUE NOT NULL,
    error_type VARCHAR(128) NOT NULL,
    normalized_message TEXT NOT NULL,
    location VARCHAR(255),
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS failures (
    id VARCHAR(36) PRIMARY KEY,
    test_run_id VARCHAR(36) NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    test_id VARCHAR(36) NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    fingerprint_id VARCHAR(36) REFERENCES fingerprints(id),
    error_type VARCHAR(128) NOT NULL,
    raw_message TEXT NOT NULL,
    normalized_message TEXT NOT NULL,
    raw_stack_trace TEXT,
    normalized_stack_trace TEXT,
    classification failure_classification NOT NULL DEFAULT 'UNKNOWN',
    classification_confidence FLOAT DEFAULT 0.5,
    flakiness_score FLOAT DEFAULT 0.0,
    regression_prob FLOAT DEFAULT 0.0,
    severity severity_level NOT NULL DEFAULT 'NORMAL',
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id VARCHAR(36) PRIMARY KEY,
    test_id VARCHAR(36) NOT NULL REFERENCES tests(id) ON DELETE CASCADE,
    build_id VARCHAR(36) NOT NULL REFERENCES builds(id) ON DELETE CASCADE,
    model_name VARCHAR(64) NOT NULL,
    model_version VARCHAR(32) DEFAULT 'v1.0',
    predicted_is_flaky BOOLEAN NOT NULL DEFAULT FALSE,
    flaky_probability FLOAT NOT NULL DEFAULT 0.0,
    features_used JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS commits (
    id VARCHAR(36) PRIMARY KEY,
    repository_id VARCHAR(36) NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    sha VARCHAR(64) UNIQUE NOT NULL,
    author_name VARCHAR(128) NOT NULL,
    author_email VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    branch VARCHAR(128) DEFAULT 'main',
    committed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS changed_files (
    id VARCHAR(36) PRIMARY KEY,
    commit_id VARCHAR(36) NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    file_path VARCHAR(255) NOT NULL,
    change_type VARCHAR(32) DEFAULT 'modified',
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    patch_summary TEXT
);

CREATE TABLE IF NOT EXISTS owners (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    team_name VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS components (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(128) UNIQUE NOT NULL,
    description TEXT,
    lead_owner_id VARCHAR(36) REFERENCES owners(id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployments (
    id VARCHAR(36) PRIMARY KEY,
    service_id VARCHAR(64) NOT NULL,
    environment VARCHAR(64) NOT NULL DEFAULT 'production',
    commit_sha VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'SUCCESS',
    deployed_by VARCHAR(128) DEFAULT 'ci-cd-bot',
    deployed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS investigations (
    id VARCHAR(36) PRIMARY KEY,
    failure_id VARCHAR(36) NOT NULL REFERENCES failures(id) ON DELETE CASCADE,
    status investigation_status NOT NULL DEFAULT 'PENDING',
    rca_summary TEXT,
    confidence rca_confidence NOT NULL DEFAULT 'MEDIUM',
    hypotheses_evaluated JSONB,
    evidence_bundle JSONB,
    assigned_to_user_id VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS remediations (
    id VARCHAR(36) PRIMARY KEY,
    investigation_id VARCHAR(36) NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    proposed_action TEXT NOT NULL,
    action_type VARCHAR(64) DEFAULT 'CODE_FIX',
    diff_or_script TEXT,
    status remediation_status NOT NULL DEFAULT 'PENDING_APPROVAL',
    approved_by_user_id VARCHAR(36) REFERENCES users(id),
    approved_at TIMESTAMP WITHOUT TIME ZONE,
    execution_result JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedbacks (
    id VARCHAR(36) PRIMARY KEY,
    investigation_id VARCHAR(36) NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    user_id VARCHAR(36) REFERENCES users(id),
    is_rca_correct BOOLEAN NOT NULL,
    actual_classification VARCHAR(64),
    comments TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) REFERENCES users(id),
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64),
    details JSONB,
    ip_address VARCHAR(64),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_failures_classification ON failures(classification);
CREATE INDEX IF NOT EXISTS idx_failures_severity ON failures(severity);
CREATE INDEX IF NOT EXISTS idx_failures_fingerprint ON failures(fingerprint_id);
CREATE INDEX IF NOT EXISTS idx_tests_repository ON tests(repository_id);
CREATE INDEX IF NOT EXISTS idx_builds_pipeline ON builds(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_builds_commit ON builds(commit_sha);
CREATE INDEX IF NOT EXISTS idx_commits_sha ON commits(sha);
