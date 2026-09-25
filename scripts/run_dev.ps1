# PowerShell script to run AG004 backend and frontend in development
Write-Host "Starting AG004 Backend on http://localhost:8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..'; .\.venv\Scripts\uvicorn.exe backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting AG004 Frontend on http://localhost:5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm run dev"

Write-Host "Both services launched in separate windows." -ForegroundColor Green
Write-Host "Backend API Docs: http://localhost:8000/docs"
Write-Host "Frontend Dashboard: http://localhost:5173"
