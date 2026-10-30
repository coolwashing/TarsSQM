@echo off
title SQM Quality System - Backend Service (:8010)

echo ====================================================================
echo           SQM Supplier Quality Management - Backend (FastAPI)
echo           Port: 8010
echo ====================================================================
echo.

cd /d "%~dp0backend"

echo [SQM] Starting FastAPI backend service...
echo [API Docs] http://localhost:8010/docs
echo [Health]   http://localhost:8010/api/health
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
if errorlevel 1 (
    echo.
    echo [ERROR] Backend failed to start. Please check the error above.
    pause
)
