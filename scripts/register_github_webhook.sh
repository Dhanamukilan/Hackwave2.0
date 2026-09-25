#!/usr/bin/env bash
# Registers GitHub repository webhook for AG004 Failure Intelligence Platform

set -euo pipefail

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_OWNER="${GITHUB_REPO_OWNER:-}"
REPO_NAME="${GITHUB_REPO_NAME:-}"
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8000/api/v1/webhooks/github}"
WEBHOOK_SECRET="${GITHUB_WEBHOOK_SECRET:-ag004-webhook-secret-token}"

if [[ -z "$GITHUB_TOKEN" || -z "$REPO_OWNER" || -z "$REPO_NAME" ]]; then
  echo "Error: GITHUB_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME must be set."
  echo "Usage: GITHUB_TOKEN=... GITHUB_REPO_OWNER=... GITHUB_REPO_NAME=... $0"
  exit 1
fi

echo "Registering webhook for https://github.com/${REPO_OWNER}/${REPO_NAME} -> ${WEBHOOK_URL}..."

curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/hooks" \
  -d @- <<EOF
{
  "name": "web",
  "active": true,
  "events": [
    "push",
    "pull_request",
    "workflow_run",
    "check_run"
  ],
  "config": {
    "url": "${WEBHOOK_URL}",
    "content_type": "json",
    "secret": "${WEBHOOK_SECRET}",
    "insecure_ssl": "0"
  }
}
EOF

echo ""
echo "Webhook registered successfully."
