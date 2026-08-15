@echo off
title Sentinel Wealth & Fraud Shield
echo =======================================================
echo    SENTINEL WEALTH & FRAUD SHIELD - STARTUP LAUNCHER
echo =======================================================
echo.

cd /d "%~dp0backend"

echo [1/3] Checking dependencies...
python -m pip install -r requirements.txt

echo [2/3] Verifying database...
python seed_data.py

echo [3/3] Starting FastAPI Server on http://127.0.0.1:8000 ...
echo.
echo Application is running!
echo Open your web browser at: http://127.0.0.1:8000
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
