#!/bin/bash
set -e

# Run build-vm.sh with prefix
./build-vm.sh 2>&1 | sed 's/^/[VM] /' | tee build-rust.log &
pid1=$!

# Run pyinstaller with prefix
uv run pyinstaller -F ray.py 2>&1 | sed 's/^/[PY] /' | tee build-py.log &
pid2=$!

wait $pid1
status1=$?
wait $pid2
status2=$?

if [[ $status1 -ne 0 || $status2 -ne 0 ]]; then
    echo "One of the tasks failed!"
    exit 1
fi
