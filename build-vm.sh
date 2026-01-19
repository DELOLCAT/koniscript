#!/bin/bash
set -euo pipefail

# Ensure the script is run from the project root
if [ ! -f "ray.py" ]; then
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "Building VM..."
pushd ray_vm > /dev/null

echo "Running tests..."
cargo test

echo "Building release version..."
cargo build --release

echo "Copying VM to dist..."
mkdir -p ../dist
cp ./target/release/ray_vm ../dist/vm

popd > /dev/null
echo "VM build successful."
