LLVM_CONFIG     ?= "llvm-config"
TARGET_TRIPLE   ?= $(shell "${LLVM_CONFIG}" --host-target)
BINARIES        := mandelbrot alphabet assign

.PHONY: all
all: ${BINARIES}

.PHONY: errors
errors: compile-errors/testbaddecl compile-errors/testbadtype

.PHONY: clean
clean:
	rm -f ${BINARIES}

%.ll: %.kal
	python -m toycomp.driver "$<" --triple "${TARGET_TRIPLE}" > "$@"

%.s: %.ll
	llc "$<" -o "$@" -mtriple "${TARGET_TRIPLE}"

%: %.s
	clang "$<" ../stdlib/lib.c ../stdlib/libmain.c -o "$@"
