#!/bin/bash
set -euo pipefail

# Ensure the script is run from the project root
if [ ! -f "src/omni_script/omni.py" ]; then
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "Building debug VM..."
pushd omni_vm > /dev/null

echo "Building debug version..."
cargo build

echo "Copying debug VM to src..."
cp ./target/debug/omni_vm ../src/omni_script/vm

popd > /dev/null
echo "Debug VM build successful."