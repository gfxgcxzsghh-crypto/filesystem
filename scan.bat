@echo off
chcp 65001 >nul
python "%~dp0fivem_scan_win.py" %*
if errorlevel 9009 (
  echo.
  echo [!] 没找到 Python。请先装 Python: https://www.python.org/downloads/
  echo     安装时务必勾选 "Add Python to PATH"
  pause
)
