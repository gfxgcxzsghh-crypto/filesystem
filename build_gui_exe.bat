@echo off
chcp 65001 >nul
echo 正在安装打包工具 pyinstaller...
python -m pip install pyinstaller
echo 正在打包 GUI 版(双击出窗口,不弹黑框)...
python -m PyInstaller --onefile --windowed --name FiveM后门扫描器 "%~dp0fivem_scanner_gui.py"
echo.
echo 打包完成! exe 在 dist 文件夹里,双击即可打开窗口。
echo 把这个 exe 发给朋友,对方双击就能用,不用装 Python。
pause
