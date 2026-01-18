# Project Overview

This project is the implementation of the "Ray" programming language, a dynamic language with a simple virtual machine. The project is split into two main parts:

1.  **Compiler:** Written in Python, it tokenizes, parses, and compiles Ray source code (`.ls` files) into bytecode (`.lsc` files). Soon, the files will change to `.ray` and `.rvm` files.
2.  **Virtual Machine (VM):** Written in Rust, it executes the compiled bytecode.

The main technologies used are Python 3.12+ and Rust. The Python part uses `typer` for the CLI, `rich` for formatted output, and `questionary` for interactive prompts. The Rust part uses `clap` for command-line argument parsing.

## Building and Running

### Python Compiler

To compile a Ray source file, use the `lolscript.py` script:

```bash
python lolscript.py compile <file.ls>
```

This will generate a `test.lsc` file in the root directory (later the filename will be configurable, and would default to the name of the source file).

To run a Ray source file directly, which compiles and then executes it with the VM:

```bash
python lolscript.py run <file.ls>
```
Please note that at the moment, additional debug features such as a copy of the source aren't available to the VM with `lolscript.py run`.

### Rust VM

To run a compiled bytecode file, use the `lolscript_vm` executable:

```bash
# First, build the VM
(cd lolscript_vm && cargo build)

# Then, run the bytecode
./lolscript_vm/target/debug/lolscript_vm run test.lsc
```

## Development Conventions

*   The Python code follows standard Python conventions and uses `mypy` for type checking.
*   The Rust code follows standard Rust conventions.
*   The language is still under development, so the bytecode format and language features are subject to change.
*   The project uses a `.gitignore` file to exclude common build and cache directories.

For any more info, consult `README.md`.