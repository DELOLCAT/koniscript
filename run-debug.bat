@echo off
setlocal

echo "Building debug VM..."
call build-debug.bat
if errorlevel 1 (
    echo "build-debug.bat failed"
    exit /b 1
)

echo "Running debug VM..."
cls
rem This is tricky to replicate without a tput equivalent.
rem I will just print a simple separator.
echo "----------------------------------------------------------------"
vm.exe %*
endlocal
