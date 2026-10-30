@echo off
title SQM Quality System - Frontend App (:3001)

echo ====================================================================
echo           SQM Supplier Quality Management - Frontend (Vue 3 + Vite)
echo           Port: 3001
echo           Backend Proxy: http://localhost:8010
echo ====================================================================
echo.

cd /d "%~dp0frontend"

echo [SQM] Starting Vite frontend dev server...
echo [App URL] http://localhost:3001
echo.

npm run dev -- --host 0.0.0.0 --port 3001
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend failed to start. Please check the error above.
    pause
)
