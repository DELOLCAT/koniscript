# Info for LLMS

This document is mainly for use for LLMS to follow, mainly to request changes that don't collide with the philosophy. LLM assisted code generation should follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)

Please also read `README.md` as well.

## Project Overview

This project is the implementation of the "OmniScript" programming language, a dynamic language with a simple virtual machine. The project is split into two main parts:

1.  **Compiler:** Written in Python, it tokenizes, parses, and compiles OmniScript source code (`.om` files) into bytecode (`.omc` files).
2.  **Virtual Machine (VM):** Written in Rust, it executes the compiled bytecode.

The main technologies used are Python 3.12+ and Rust. The Python part uses `typer` for the CLI, `rich` for formatted output, and `questionary` for interactive prompts. The Rust part uses `clap` for command-line argument parsing.

### Building and Running

#### Python Compiler

To compile a OmniScript source file, use the `omni.py` script:

```bash
python src/omni_script/omni.py compile <file.om>
```

This will generate a `test.lsc` file in the root directory (later the filename will be configurable, and would default to the name of the source file).

To run a OmniScript source file directly, which compiles and then executes it with the VM:

```bash
python src/omni_script/omni.py run <file.om>
```
Please note that at the moment, additional debug features such as a copy of the source aren't available to the VM with `omni.py run`.

#### Rust VM

To run a compiled bytecode file, use the `omni_vm` executable:

```bash
# First, build the VM
(cd omni_vm && cargo build)

# Then, run the bytecode
./omni_vm/target/debug/omni_vm run test.omc
```

### Development Conventions

* The Python code follows standard Python conventions and uses `mypy` for type checking.
* The Rust code follows standard Rust conventions.
* The language is still under development, so the bytecode format and language features are subject to change.
* The project uses a `.gitignore` file to exclude common build and cache directories.
