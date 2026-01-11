#!/bin/bash

set -e

cd /home/ahmad/coding/rpn/lolscript_vm
cargo test
cargo build -r
cp /home/ahmad/coding/rpn/lolscript_vm/target/release/lolscript_vm /home/ahmad/coding/rpn/vm