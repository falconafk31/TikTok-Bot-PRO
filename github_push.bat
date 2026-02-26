@echo off
setlocal enabledelayedexpansion
echo [TIKTOK BOT PRO] Preparing to Push to GitHub...

REM Check if Git is initialized
if not exist .git (
    echo [INIT] Initializing Git repository...
    git init
)

REM Check for remote origin
git remote get-url origin >nul 2>&1
if !errorlevel! neq 0 (
    echo.
    echo [REMOTE] Remote origin belum diatur.
    set /p repo_url="Masukkan URL Repositori GitHub (contoh: https://github.com/username/repo.git): "
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
set /p commit_msg="Masukkan pesan update (kosongkan untuk 'Regular Update'): "
if "!commit_msg!"=="" set commit_msg=Regular Update - TikTok Bot PRO

echo [STAGING] Adding files...
git add .

echo [COMMIT] Committing changes...
git commit -m "!commit_msg!"

echo [PUSHING] Uploading code to GitHub...
git push origin main

if !errorlevel! neq 0 (
    echo.
    echo [ERROR] Gagal melakukan push. Pastikan koneksi internet aktif dan URL remote benar.
    echo Jika ini repository baru, coba jalankan: git push -u origin main --force
) else (
    echo.
    echo [DONE] Proyek berhasil diperbarui di GitHub!
)

pause
