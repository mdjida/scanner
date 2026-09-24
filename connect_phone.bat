:start
@echo off
echo.
echo  Live Comp Phone USB Tunnel
echo.
echo  This connects your phone to the PC backend over the USB cable.
echo.
echo  BEFORE running this, you MUST enable USB debugging on your phone:
echo.
echo   1. Settings -> About phone -> tap "Build number" 7 times
echo   2. Settings -> System -> Developer options -> turn ON "USB debugging"
echo   3. Plug phone into PC with a USB cable
echo   4. Tap "Allow" on the phone when it asks about USB debugging
echo.
echo  Then run this file again.
echo.

set "ADB=C:\Users\M\LiveCompOverlay\tools\platform-tools\adb.exe"

if not exist "%ADB%" (
    echo ADB not found. Please run start_backend.ps1 first or check the tools folder.
    pause
    exit /b 1
)

"%ADB%" devices
"%ADB%" reverse tcp:8000 tcp:8000

if %errorlevel% neq 0 (
    echo.
    echo FAILED. Make sure USB debugging is enabled and the phone is plugged in.
    pause
    exit /b 1
)

echo.
echo SUCCESS. In the Android app, use this backend URL:
echo    http://localhost:8000
echo.
pause
