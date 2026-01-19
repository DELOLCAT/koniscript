#!/bin/bash

set -e

cd ./ray_vm
cargo build
cp ./target/debug/ray_vm /home/ahmad/coding/rpn/vm