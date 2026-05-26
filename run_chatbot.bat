@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    .venv\Scripts\pip install -r requirements.txt -q
)
echo Starting Local RAG Chatbot...
echo Open http://127.0.0.1:7860 in your browser after it starts.
.venv\Scripts\python -m src serve
pause
