#!/bin/bash
set -e

cd ./ray_vm
cargo test
cargo build -r
mkdir -p ./build
cp ./target/release/ray_vm ../dist/vm