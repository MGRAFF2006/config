@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\OEM\setup.ps1
exit /b %errorlevel%
