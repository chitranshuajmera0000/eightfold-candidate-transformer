@echo off
echo =========================================
echo Starting Candidate ETL Pipeline UI
echo =========================================

IF NOT EXIST "venv" (
    echo [1/3] Creating Python virtual environment...
    python -m venv venv
    echo [2/3] Activating and installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt >nul 2>&1
) ELSE (
    echo [1/3] Virtual environment found. Booting instantly...
    call venv\Scripts\activate.bat
)

echo [3/3] Starting Flask server...
echo The UI will automatically open in your default browser.
echo Press CTRL+C in this window to stop the server.
echo.

start http://localhost:5000
python app.py

pause
