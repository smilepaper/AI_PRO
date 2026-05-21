@echo off
REM AI Gesture Control - Windows run script

REM If a virtual environment exists, activate it; otherwise create one and install deps
if exist ".venv\Scripts\activate.bat" (
  call .venv\Scripts\activate.bat
) else (
  echo No .venv found. Creating virtual environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  echo Installing dependencies from requirements.txt...
  pip install -r requirements.txt
)

echo Starting gesture_app.py
python gesture_app.py

echo Application exited. Press any key to close.
pause >nul
