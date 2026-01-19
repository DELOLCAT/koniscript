#!/bin/bash
PAST_DIR=$(pwd)

cd /home/ahmad/coding/rpn/ray_vm
cargo test
cargo build
cd $PAST_DIR
printf "\033[2J"
printf "$(tput setaf 6)%$(tput cols)s$(tput sgr0)\n" | tr ' ' '-'
/home/ahmad/coding/rpn/ray_vm/target/debug/ray_vm "$@"