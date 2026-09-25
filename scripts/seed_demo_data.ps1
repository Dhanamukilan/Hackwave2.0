# PowerShell script to seed all demo scenarios into local database and vector store
Write-Host "Seeding AG004 demo scenarios..." -ForegroundColor Cyan
& .\.venv\Scripts\python.exe database\seed_data\seed_demo_scenarios.py
Write-Host "Seeding complete." -ForegroundColor Green
