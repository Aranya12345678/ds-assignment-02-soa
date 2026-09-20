@echo off
echo Starting gRPC Fraud Detection Server...
start "gRPC Server" cmd /k "venv\Scripts\activate && python server.py"

timeout /t 2 /nobreak >nul

echo Starting Gateway...
start "Gateway" cmd /k "cd gateway && ..\venv\Scripts\activate && python app.py"

echo.
echo Both services starting in separate windows.
echo Once both show "running", you can test with:
echo   cd soap-client
echo   ..\venv\Scripts\activate
echo   python soap_client.py
echo.
pause