#!/bin/bash

set -e

cd /home/ahmad/coding/rpn/ray_vm
cargo test
cargo build -r
cp /home/ahmad/coding/rpn/ray_vm/target/release/ray_vm /home/ahmad/coding/rpn/vm