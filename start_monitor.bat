@echo off
REM AIOS Agent Monitor Launcher
cd /d C:\Users\A\.openclaw\workspace\aios\agent_system
start /B "" "C:\Program Files\Python312\python.exe" -m http.server 18793
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:18793/monitor.html"
exit
