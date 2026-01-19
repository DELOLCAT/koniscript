#!/bin/bash

set -e

cd /home/ahmad/coding/rpn/ray_vm
cargo build
cp /home/ahmad/coding/rpn/ray_vm/target/debug/ray_vm /home/ahmad/coding/rpn/vm