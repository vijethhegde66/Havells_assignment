@echo off
echo ========================================
echo Restoring Development Environment
echo ========================================
echo.

if exist .env.backup (
    copy .env.backup .env >nul
    echo [OK] Credentials restored from .env.backup
    echo.
    echo Your development environment is ready.
) else (
    echo [ERROR] .env.backup not found!
    echo.
    echo Please manually create .env file with your credentials.
)

echo.
pause
