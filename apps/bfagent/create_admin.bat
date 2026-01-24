@echo off
echo ========================================
echo Django Superuser Setup
echo ========================================
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Running superuser script...
python create_superuser.py

pause
