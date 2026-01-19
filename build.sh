#!/bin/bash
set -euo pipefail

# Ensure the script is run from the project root
if [ ! -f "src/ray.py" ]; then
    echo "Please run this script from the project root directory."
    exit 1
fi

# Function to prefix output
prefix_output() {
    local prefix=$1
    local color=$2
    awk -v prefix="$prefix" -v color="$color" '{print "\033[1;" color "m[" prefix "]\033[0m " $0}'
}

echo "Starting parallel build..."

# Run VM build in background and pipe output
./build-vm.sh 2>&1 | prefix_output "VM" "34" | tee build-vm.log &
vm_pid=$!

# Run PyInstaller build in background and pipe output
uv run pyinstaller -F src/ray.py 2>&1 | prefix_output "PY" "32" | tee build-py.log &
py_pid=$!

# Wait for both and get exit codes
wait $vm_pid
vm_status=$?
wait $py_pid
py_status=$?

# Check statuses and report
if [ $vm_status -ne 0 ]; then
    echo -e "\033[1;31m[VM] build failed! Check build-vm.log\033[0m"
fi

if [ $py_status -ne 0 ]; then
    echo -e "\033[1;31m[PY] build failed! Check build-py.log\033[0m"
fi

if [ $vm_status -ne 0 ] || [ $py_status -ne 0 ]; then
    echo -e "\033[1;31mBuild failed.\033[0m"
    exit 1
else
    echo -e "\033[1;32mAll builds successful.\033[0m"
fi
