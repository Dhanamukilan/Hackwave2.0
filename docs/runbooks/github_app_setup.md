# Runbook: Setting Up GitHub App / Personal Access Token for AG004

This runbook guides connecting your real GitHub repository to the AG004 Failure Intelligence Platform.

---

## Option 1: Personal Access Token (PAT) — Quickest Setup

1. In GitHub, navigate to **Settings &rarr; Developer Settings &rarr; Personal access tokens &rarr; Fine-grained tokens** (or Tokens classic).
2. Generate a token with the following scopes:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
3. Copy the token into your `.env` file:
   ```bash
   GITHUB_TOKEN=ghp_yourGeneratedTokenHere...
   GITHUB_REPO_OWNER=your-org-or-username
   GITHUB_REPO_NAME=your-repo-name
   ```
4. Register the webhook pointing to your AG004 backend:
   ```bash
   bash scripts/register_github_webhook.sh
   ```

---

## Option 2: Webhook Only (No Token Required)

1. Open your GitHub Repository &rarr; **Settings &rarr; Webhooks &rarr; Add webhook**.
2. **Payload URL:** `http://<your-host-or-ngrok>:8000/api/v1/webhooks/github`
3. **Content type:** `application/json`
4. **Secret:** Set to `GITHUB_WEBHOOK_SECRET` from your `.env` (default: `ag004-webhook-secret-token`).
5. **Which events would you like to trigger this webhook?**
   - Select: `Push`, `Pull requests`, `Workflow runs`, `Check runs`.
6. Save webhook.

When a workflow runs in your repository, AG004 will automatically receive events and ingest test failure logs.
