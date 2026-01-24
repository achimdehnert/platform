@echo off
REM ==========================================
REM Django Development Server mit SQLite
REM ==========================================

echo.
echo ========================================
echo  Django mit SQLite starten
echo ========================================
echo.

REM Aktiviere venv
echo [1/3] Aktiviere Virtual Environment...
call .venv\Scripts\activate.bat

REM Setze Environment
echo [2/3] Setze Environment Variables...
set DJANGO_SETTINGS_MODULE=config.settings.development
set USE_POSTGRES=false

REM Check Django
echo [3/3] Starte Django Server...
echo.
python manage.py check
if errorlevel 1 (
    echo.
    echo ❌ Django Check failed!
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Django Check OK!
echo ✅ Using SQLite Database
echo.
echo Starting server on http://localhost:8000...
echo.

python manage.py runserver 8000

pause
