@echo off
REM Start the Live Comp Overlay backend on Windows.
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
