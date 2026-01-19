@echo off
setlocal

echo "Building VM..."
call build-vm.bat > build-vm.log 2>&1
if errorlevel 1 (
  echo "VM build failed. Check build-vm.log"
  type build-vm.log
  exit /b 1
)

echo "Building with PyInstaller..."
uv run pyinstaller -F ray.py > build-py.log 2>&1
if errorlevel 1 (
  echo "PyInstaller build failed. Check build-py.log"
  type build-py.log
  exit /b 1
)

echo "All builds successful."
endlocal
