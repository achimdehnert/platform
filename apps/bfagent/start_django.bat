@echo off
echo ========================================
echo Starting Django Development Server
echo ========================================
echo.
echo 1. Activating virtual environment...
call venv\Scripts\activate.bat

echo 2. Setting Django settings...
set DJANGO_SETTINGS_MODULE=config.settings.development

echo 3. Starting server on port 8000...
python manage.py runserver 8000

pause
