#!/bin/bash
set -e

cd ./ray_vm
cargo test
cargo build -r
cp ./ray_vm/target/release/ray_vm ./vm