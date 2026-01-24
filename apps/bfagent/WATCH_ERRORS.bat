@echo off
REM ===============================================
REM ERROR WATCHER - TESTMODUS
REM ===============================================
echo.
echo =========================================
echo   ERROR WATCHER - TESTMODUS
echo =========================================
echo.
echo Aktiviert: Autonome Error Detection
echo Funktion: Zeigt Fehler live an
echo Modus: Interaktiv mit Cascade
echo.
echo =========================================
echo.

REM Aktiviere Virtual Environment
call .venv\Scripts\activate.bat

REM Starte Watcher
python watch_errors.py

pause
