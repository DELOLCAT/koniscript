@echo off
setlocal

pushd omni_vm
if errorlevel 1 (
    echo "Failed to cd into omni_vm"
    exit /b 1
)

cargo test
if errorlevel 1 (
    echo "cargo test failed"
    popd
    exit /b 1
)

cargo build --release
if errorlevel 1 (
    echo "cargo build --release failed"
    popd
    exit /b 1
)

if not exist ".\build" mkdir ".\build"
copy ".\target\release\omni_vm.exe" "..\dist\vm.exe"
if errorlevel 1 (
    echo "Failed to copy vm"
    popd
    exit /b 1
)

popd
endlocal


