@echo off
title SQM Quality System - Backend Service (:8010)

echo ====================================================================
echo           SQM Supplier Quality Management - Backend (FastAPI)
echo           Port: 8010
echo ====================================================================
echo.

cd /d "%~dp0backend"

python -c "import openpyxl, requests, pypdf" >nul 2>&1
if errorlevel 1 (
    echo [SQM] Installing missing backend dependencies...
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [ERROR] Backend dependency installation failed.
        pause
        exit /b 1
    )
)

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
