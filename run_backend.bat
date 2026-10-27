@echo off
cd /d "%~dp0backend"
"C:\Users\20122\PyCharmMiscProject\.venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
