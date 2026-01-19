#!/bin/bash
set -o pipefail

./build-vm.sh 2>&1 | awk '{print "\033[1;34m[VM]\033[0m " $0}' | tee build-rust.log &
pid1=$!

uv run pyinstaller -F ray.py 2>&1 | awk '{print "\033[1;32m[PY]\033[0m " $0}' | tee build-py.log &
pid2=$!

wait $pid1
status1=$?
wait $pid2
status2=$?

if [[ $status1 -ne 0 || $status2 -ne 0 ]]; then
    [[ $status1 -ne 0 ]] && echo -e "\033[1;31m[VM] failed! Check build-rust.log\033[0m"
    [[ $status2 -ne 0 ]] && echo -e "\033[1;31m[PY] failed! Check build-py.log\033[0m"
fi
