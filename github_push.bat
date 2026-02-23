@echo off
echo [TIKTOK BOT PRO] Preparing to Push to GitHub...

REM Initialize if not already
if not exist .git (
    git init
)

REM Ensure local config exists (Fixes "src refspec main does not match any")
git config user.email >nul 2>&1
if %errorlevel% neq 0 (
    echo [CONFIG] Setting temporary git user...
    git config user.email "user@example.com"
    git config user.name "Bot User"
)

git add .
git commit -m "Initial commit - TikTok Bot PRO"

echo.
set /p repo_url="Masukkan URL Repositori GitHub Baru (contoh: https://github.com/username/repo.git): "
if "%repo_url%"=="" (
    echo Error: URL tidak boleh kosong!
    pause
    exit /b
)

REM Remove existing origin to avoid "already exists" error
git remote remove origin >nul 2>&1
git remote add origin %repo_url%
git branch -M main

echo [PUSHING] Uploading code... silakan login jika muncul popup.
git push -u origin main --force

echo.
echo [DONE] Proyek berhasil di-push ke GitHub!
pause
