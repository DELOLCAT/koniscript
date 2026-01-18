# Project Overview

This project is the implementation of the "Ray" programming language, a dynamic language with a simple virtual machine. The project is split into two main parts:

1.  **Compiler:** Written in Python, it tokenizes, parses, and compiles Ray source code (`.ray` files) into bytecode (`.rvm` files).
2.  **Virtual Machine (VM):** Written in Rust, it executes the compiled bytecode.

The main technologies used are Python 3.12+ and Rust. The Python part uses `typer` for the CLI, `rich` for formatted output, and `questionary` for interactive prompts. The Rust part uses `clap` for command-line argument parsing.

## Building and Running

### Python Compiler

To compile a Ray source file, use the `ray.py` script:

```bash
python ray.py compile <file.ray>
```

This will generate a `test.lsc` file in the root directory (later the filename will be configurable, and would default to the name of the source file).

To run a Ray source file directly, which compiles and then executes it with the VM:

```bash
python ray.py run <file.ray>
```
Please note that at the moment, additional debug features such as a copy of the source aren't available to the VM with `ray.py run`.

### Rust VM

To run a compiled bytecode file, use the `ray_vm` executable:

```bash
# First, build the VM
(cd ray_vm && cargo build)

# Then, run the bytecode
./ray_vm/target/debug/ray_vm run test.lsc
```

## Development Conventions

*   The Python code follows standard Python conventions and uses `mypy` for type checking.
*   The Rust code follows standard Rust conventions.
*   The language is still under development, so the bytecode format and language features are subject to change.
*   The project uses a `.gitignore` file to exclude common build and cache directories.

For any more info, consult `README.md`.