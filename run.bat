@echo off
title HackHERway PS6 - AI Access Approval
echo ============================================
echo   HackHERway PS6 - End to End Launcher
echo ============================================
echo.

REM --- Backend Setup ---
echo [1/4] Setting up backend virtual environment...
cd /d "%~dp0backend"

if not exist .venv (
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing backend dependencies...
pip install -r requirements.txt -q

echo [3/4] Seeding database...
python scripts/seed_sqlite.py

echo [4/4] Starting backend on port 8000...
start "Backend - FastAPI" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate.bat && uvicorn src.main:app --reload --port 8000"

REM --- Frontend Setup ---
cd /d "%~dp0frontend"

echo.
echo [Frontend] Installing dependencies...
call npm install

echo [Frontend] Starting frontend on port 3000...
start "Frontend - Next.js" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Both servers are starting in new windows:
echo     Backend:  http://localhost:8000
echo     Frontend: http://localhost:3000
echo ============================================
echo.
echo Close this window or press any key to exit.
pause >nul
