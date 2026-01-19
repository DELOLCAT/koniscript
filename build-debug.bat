@echo off
setlocal

pushd ray_vm
if errorlevel 1 (
    echo "Failed to cd into ray_vm"
    exit /b 1
)

cargo build
if errorlevel 1 (
    echo "cargo build failed"
    popd
    exit /b 1
)

copy ".\target\debug\ray_vm.exe" "..\vm.exe"
if errorlevel 1 (
    echo "Failed to copy vm"
    popd
    exit /b 1
)

popd
endlocal

