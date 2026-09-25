# Registers GitHub repository webhook for AG004 Failure Intelligence Platform
param(
    [string]$WebhookUrl = "http://localhost:8000/api/v1/webhooks/github"
)

# Load from .env if present
if (Test-Path "$PSScriptRoot\..\.env") {
    Get-Content "$PSScriptRoot\..\.env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            $name = $parts[0].Trim()
            $val = $parts[1].Trim()
            if (-not [System.Environment]::GetEnvironmentVariable($name)) {
                [System.Environment]::SetEnvironmentVariable($name, $val)
            }
        }
    }
}

$token = $env:GITHUB_TOKEN
$owner = $env:GITHUB_REPO_OWNER
$repo = $env:GITHUB_REPO_NAME
$secret = $env:GITHUB_WEBHOOK_SECRET

if (-not $token -or -not $owner -or -not $repo) {
    Write-Error "Error: GITHUB_TOKEN, GITHUB_REPO_OWNER, and GITHUB_REPO_NAME must be set in environment or .env file."
    exit 1
}

Write-Host "Registering webhook for https://github.com/$owner/$repo -> $WebhookUrl..." -ForegroundColor Cyan

$headers = @{
    "Accept" = "application/vnd.github+json"
    "Authorization" = "Bearer $token"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$body = @{
    name = "web"
    active = $true
    events = @("push", "pull_request", "workflow_run", "check_run")
    config = @{
        url = $WebhookUrl
        content_type = "json"
        secret = $secret
        insecure_ssl = "0"
    }
} | ConvertTo-Json -Depth 5

try {
    $res = Invoke-RestMethod -Uri "https://api.github.com/repos/$owner/$repo/hooks" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "Webhook registered successfully! ID: $($res.id)" -ForegroundColor Green
} catch {
    $err = $_.Exception.Response
    if ($err.StatusCode -eq 422) {
        Write-Host "Webhook already exists or configured on target repository." -ForegroundColor Yellow
    } else {
        Write-Error "Failed to register webhook: $_"
    }
}
