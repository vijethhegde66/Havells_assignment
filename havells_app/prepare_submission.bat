@echo off
echo ========================================
echo Preparing Submission Package
echo ========================================
echo.

echo Step 1: Backing up .env file...
if exist .env (
    copy .env .env.backup >nul
    echo [OK] .env backed up to .env.backup
) else (
    echo [SKIP] No .env file found
)

echo.
echo Step 2: Removing .env from submission...
if exist .env (
    del .env
    echo [OK] .env removed
)

echo.
echo Step 3: Verifying .env.example exists...
if exist .env.example (
    echo [OK] .env.example present
) else (
    echo [ERROR] .env.example missing!
    pause
    exit /b 1
)

echo.
echo Step 4: Cleaning Python cache...
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo [OK] __pycache__ removed
)

echo.
echo Step 5: Cleaning test outputs...
if exist test_transcripts (
    rmdir /s /q test_transcripts
    echo [OK] test_transcripts removed (will be regenerated)
)

echo.
echo Step 6: Verifying core files...
set MISSING=0

if not exist agent.py (
    echo [ERROR] agent.py missing!
    set MISSING=1
)
if not exist device.py (
    echo [ERROR] device.py missing!
    set MISSING=1
)
if not exist reset_detector.py (
    echo [ERROR] reset_detector.py missing!
    set MISSING=1
)
if not exist scenarios.py (
    echo [ERROR] scenarios.py missing!
    set MISSING=1
)
if not exist README.md (
    echo [ERROR] README.md missing!
    set MISSING=1
)
if not exist DESIGN_NOTE.md (
    echo [ERROR] DESIGN_NOTE.md missing!
    set MISSING=1
)

if %MISSING%==0 (
    echo [OK] All core files present
) else (
    echo [ERROR] Some core files missing!
    pause
    exit /b 1
)

echo.
echo Step 7: Running tests to generate transcripts...
python scenarios.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Tests failed!
    pause
    exit /b 1
)
echo [OK] Tests completed

echo.
echo Step 8: Verifying transcripts generated...
if exist test_transcripts\SUMMARY.md (
    echo [OK] Transcripts generated
) else (
    echo [ERROR] Transcripts not generated!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Submission Package Ready!
echo ========================================
echo.
echo Files prepared in current directory.
echo.
echo To restore your credentials later:
echo   copy .env.backup .env
echo.
echo To create submission zip:
echo   1. Go to parent directory
echo   2. Right-click havells_app folder
echo   3. Send to > Compressed (zipped) folder
echo.
echo Or use: tar -czf submission.zip havells_app
echo.
pause
