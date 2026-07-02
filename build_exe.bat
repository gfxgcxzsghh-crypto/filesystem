@echo off
chcp 65001 >nul
echo 正在安装打包工具 pyinstaller...
python -m pip install pyinstaller
echo 正在打包...
python -m PyInstaller --onefile --name FiveM_Scan "%~dp0fivem_scan_win.py"
echo.
echo 打包完成! exe 在 dist 文件夹里,可以把资源文件夹拖到 exe 上运行。
pause
