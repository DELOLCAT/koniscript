# Info for LLMS

This document is mainly for use for LLMS to follow, mainly to request changes that don't collide with the philosophy. LLM assisted code generation should follow the guidelines in [CONTRIBUTING.md](CONTRIBUTING.md)

Please also read `README.md` as well.

## Project Overview

This project is the implementation of the "OmniScript" programming language, a dynamic language with a simple virtual machine. The project is split into two main parts:

1. **Compiler:** Written in Python, it tokenizes, parses, and compiles OmniScript source code (`.om` files) into bytecode (`.omc` files).
2. **Virtual Machine (VM):** Written in Rust, it executes the compiled bytecode.

The main technologies used are Python 3.12+ and Rust. The Python part uses `typer` for the CLI, `rich` for formatted output, and `questionary` for interactive prompts. The Rust part uses `clap` for command-line argument parsing.

### Building and Running

#### Python Compiler

To compile a OmniScript source file, use the `omni.py` script:

```bash
uv run omni compile <file.om>
```

This will generate a `.omc` file with the same name as the source in the same directory as the source.

To run a OmniScript source file directly, which compiles and then executes it with the VM:

```bash
uv run omni run <file.om>
```

Please note that at the moment, additional debug features such as a copy of the source aren't available to the VM with `omni.py run`.

#### Rust VM

To run a compiled bytecode file, use the `omvm` executable:

```bash
# First, build the VM
uv run build_vm.py

# Then, run the bytecode
./dist/omvm run {filepath}.omc
```

### Development Conventions

* The Python code follows standard Python conventions and uses `pyright` for type checking.
* The Rust code follows standard Rust conventions.
* The language is still under development, so the bytecode format and language features are subject to change.
* The project uses a `.gitignore` file to exclude common build and cache directories.
