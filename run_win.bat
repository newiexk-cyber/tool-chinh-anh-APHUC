@echo off
chcp 65001 >nul
title Auto Retouch Studio - MAGIMIR

echo ======================================================================
echo    MUNCI STUDIO - AUTO RETOUCH AUTOMATION (MAGIMIR DESKTOP)
echo ======================================================================
echo.

if exist "%~dp0app.py" (
    cd /d "%~dp0"
) else (
    cd /d "C:\memay\photo-retouch-automation"
)

echo Thu muc lam viec: %CD%
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Python tren he thong!
    pause
    exit /b 1
)

echo [1/2] Dang kiem tra thu vien...
python -m streamlit --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Dang cai dat cac thu vien con thieu...
    python -m pip install -r requirements.txt
)

echo.
echo [2/2] Dang khoi dong Web Dashboard (Streamlit)...
echo Dia chi truy cap: http://localhost:8501
echo.
python -m streamlit run app.py

pause
