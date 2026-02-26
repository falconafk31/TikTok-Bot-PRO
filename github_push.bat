@echo off
setlocal enabledelayedexpansion
echo ======================================================
echo           TIKTOK BOT PRO - GITHUB DEPLOYER
echo ======================================================
echo [SYSTEM] Mempersiapkan update ke VPS via GitHub...
echo.

REM Check if Git is initialized
if not exist .git (
    echo [INIT] Inisialisasi Git repository...
    git init
)

REM Check for remote origin
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo [REMOTE] Remote origin belum diatur.
    set /p repo_url="Masukkan URL Repositori GitHub (URL HTTPS): "
    if "!repo_url!"=="" (
        echo Error: URL tidak boleh kosong!
        pause
        exit /b
    )
    git remote add origin !repo_url!
) else (
    for /f "tokens=*" %%a in ('git remote get-url origin') do set current_url=%%a
    echo [REMOTE] Terhubung ke: !current_url!
)

REM Set branch to main
git branch -M main

REM Ask for commit message
echo.
set /p commit_msg="Detail Update (Kosongkan utk 'Update Dashboard Pro'): "
if "!commit_msg!"=="" set commit_msg=Update Dashboard Pro - Unified System V4

echo.
echo [STAGING] Mengumpulkan file (dashboard_pro.py, bot.py, dll)...
git add .

echo [COMMIT] Mengunci perubahan...
git commit -m "!commit_msg!"

echo [PUSHING] Mengunggah kode ke GitHub...
git push origin main

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Gagal upload! Cek koneksi atau jalankan: git push -u origin main --force
) else (
    echo.
    echo ======================================================
    echo [DONE] Misi Berhasil! Kode sudah aman di GitHub.
    echo [NEXT] Sekarang di VPS Anda: git pull && docker compose up -d --build
    echo ======================================================
)

pause
