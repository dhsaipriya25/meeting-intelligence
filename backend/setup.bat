@echo off
echo Setting up Meeting Intelligence Backend...
python -m venv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Done! Run start.bat to launch the server.
pause
