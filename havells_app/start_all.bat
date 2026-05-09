@echo off
echo ========================================
echo Smart Device Control Agent
echo ========================================
echo.
echo Starting Backend and Frontend...
echo.

start "Backend API" cmd /k "cd backend && python api.py"
timeout /t 3 /nobreak > nul

start "Frontend UI" cmd /k "cd frontend && streamlit run app.py"

echo.
echo ========================================
echo Services Started!
echo ========================================
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:8501
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press any key to stop all services...
pause > nul

taskkill /FI "WINDOWTITLE eq Backend API*" /T /F
taskkill /FI "WINDOWTITLE eq Frontend UI*" /T /F
