#!/bin/bash

TARGET_TRIPLE="$(llvm-config --host-target)"

python -m toycomp.driver "$1" --triple "$TARGET_TRIPLE" > a.ll
llc a.ll -o a.s -mtriple "$TARGET_TRIPLE"
clang a.ll lib.c libmain.c
