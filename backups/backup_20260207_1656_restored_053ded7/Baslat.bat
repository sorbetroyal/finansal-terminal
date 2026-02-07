@echo off
TITLE Finansal Terminal Launcher
chcp 65001 > nul

echo ==========================================
echo    Finansal Terminal Başlatılıyor...
echo ==========================================

:: Proje dizinine git
cd /d "%~dp0"

:: Sanal ortam kontrolü ve çalıştırma
if exist ".venv\Scripts\python.exe" (
    echo [BILGI] Sanal ortam bulundu.
    echo [BILGI] Uygulama başlatılıyor, lütfen bekleyin...
    ".venv\Scripts\python.exe" launcher.py
) else (
    echo [HATA] .venv klasörü bulunamadı!
    echo Lütfen .venv klasörünün proje dizininde olduğundan emin olun.
    echo.
    pause
)
