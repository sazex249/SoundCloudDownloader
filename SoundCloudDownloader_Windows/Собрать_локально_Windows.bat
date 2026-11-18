@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto fail
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail
py -m PyInstaller --noconfirm --clean --onefile --windowed --name SoundCloudDownloader --collect-all yt_dlp soundcloud_downloader.py
if errorlevel 1 goto fail
echo.
echo EXE created: dist\SoundCloudDownloader.exe
pause
exit /b 0
:fail
echo Build failed. Review the errors above.
pause
exit /b 1
