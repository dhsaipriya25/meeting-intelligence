@echo off
call venv\Scripts\activate
set /p GROQ_KEY="Enter your Groq API Key: "
set GROQ_API_KEY=%GROQ_KEY%
uvicorn main:app --reload --port 8000
