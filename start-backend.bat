@echo off
cd /d "E:\New Projects\Arc\generic-data-rag-agent\backend"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
pause