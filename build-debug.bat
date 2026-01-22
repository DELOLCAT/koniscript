@echo off
setlocal

pushd omni_vm
if errorlevel 1 (
    echo "Failed to cd into omni_vm"
    exit /b 1
)

cargo build
if errorlevel 1 (
    echo "cargo build failed"
    popd
    exit /b 1
)

copy ".\target\debug\omni_vm.exe" "src\omni_script\vm.exe"
if errorlevel 1 (
    echo "Failed to copy vm"
    popd
    exit /b 1
)

popd
endlocal

