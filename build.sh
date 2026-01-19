#!/bin/bash

set -e

./build-vm.sh
uv run pyinstaller -F ray.py