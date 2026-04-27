#!/bin/bash
set -euo pipefail

# Ensure the script is run from the project root
if [ ! -f "src/koni.py" ]; then
    echo "Please run this script from the project root directory."
    exit 1
fi

echo "Building debug VM..."
./build-debug.sh

echo "Running debug VM..."
printf "\033[2J" # Clear screen
printf "%$(tput cols)s\n" | tr ' ' '-' | tput setaf 6; tput sgr0 # Print separator

./vm "$@"