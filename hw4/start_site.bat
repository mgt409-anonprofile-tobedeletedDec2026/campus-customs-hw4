@echo off
REM Double-click to start Campus Customs. Close the two windows it opens to stop it.
cd /d "%~dp0"
start "Campus Customs backend" cmd /k "cd backend && ..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000 --timeout-graceful-shutdown 3"
start "Campus Customs website" cmd /k "cd frontend && npm run dev"
timeout /t 5 /nobreak >nul
start "" http://localhost:5173
