@echo off
title SQM Quality System - Dev Launcher (Port: 8010 + 3001)

echo ====================================================================
echo           SQM Supplier Quality Management System
echo           Backend Port:  8010
echo           Frontend Port: 3001
echo ====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Launching FastAPI backend server on port 8010...
start "SQM Backend (:8010)" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8010"

echo [2/3] Launching Vue 3 Vite frontend server on port 3001...
start "SQM Frontend (:3001)" cmd /k "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 3001"

echo.
echo [3/3] Development services launched successfully!
echo --------------------------------------------------------------------
echo   Frontend Web UI:   http://localhost:3001
echo   Backend API Docs:  http://localhost:8010/docs
echo   Backend Health:    http://localhost:8010/api/health
echo --------------------------------------------------------------------
echo Tips:
echo   - To start individually, run start_backend.bat or start_frontend.bat
echo   - Closing this window will NOT stop backend/frontend background windows
echo --------------------------------------------------------------------
echo Press any key to exit this launcher...
pause >nul
