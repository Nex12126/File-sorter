@echo off
setlocal
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed --add-data "classification_rules.json;." --name DateiSortierer main.py
if errorlevel 1 exit /b 1
echo.
echo Fertig: dist\DateiSortierer.exe
endlocal