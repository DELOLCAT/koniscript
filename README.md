# OmniScript: Write once, run wherever you want

## NOTICE: OmniScript is still indev, expect breaking changes

For contributing, see [CONTRIBUTING.md](CONTRIBUTING.md)

OmniScript is a dynamic programming language that focuses on these main features:

- A simple VM (OmniVM) that you could implement almost anywhere - even in Scratch mods
- Readability of code
- Ease of packaging (code compiles down to a single .omc bytecode file)
- Compatibility: Supports @require flags (ex. @require fs, gui) so OmniScript can work smoothly across multiple runtime environments. This system is indev, so expect better features in the near future.

## Table of contents

- [Currently Implemented Features](#currently-implemented-features)
- [Usage](#usage)
  - [Writing a program](#writing-a-program)
  - [CLI](#cli)
- [Roadmap](#roadmap)
  - [Language](#language)
  - [App](#app)
- [Build](#build)
  - [Prerequisites](#prerequisites)
  - [Steps](#steps)

## Currently implemented features

- Variables
- Functions
- Basic builtins (print, input, to_(type))
- Arrays (methods indev)
- The requirements syntax

## Usage

### Writing a program

Since OmniScript is still in early development, there aren't many features.

- Types: `"string"`, integer: `2`, float: `3.14`, and booleans `true`/`false`
- Functions: `name(args)`
- Comments (multi-line soon): `# I am a comment`

Example:

```omniscript
print("foo, bar", " baz") # The print function takes multiple arguments, and concatenates them (without a space)
```

- Variables:

```omniscript
this_is_a_var = "foo"
print(this_is_a_var)
```

- Arithmetic:

```omniscript
print(5 + 5 / 2)
```

- Conditionals:

```omniscript
num = input("Enter a number\n>>> ") # The input function prints a message and waits for user input, returning the input given by the user.

print(num == 5)
if num == 5 {
  print("The number is equal to 5")
} else if num == 10 {
  print("The number is equal to 10")
} else {
  print("The number is not equal to 5 or 10")
}
```

- Functions (and recursion):

```omniscript
func fib(n) {
  if n <= 1 {
    return n
  }
  return fib(n - 1) + fib(n - 2)
}

print(fib(10)) # => 55
```

- Requirements: `@require fs, gpu` (indev, expect more features)

### CLI

To run a program, use `omni run`:

```bash
$ omni run examples/fib.om 
55
```

To compile a program, use `omni compile`:

```bash
$ omni compile examples/fib.om
Compiling with debug (source+line info). See `omni compile --help` for more info
Wrote to examples/fib.omc
```

To run compiled programs, use `omvm run`:

```bash
$ omvm run ./examples/fib.omc
55
```

## Roadmap

| Icon                | Meaning                       |
|---------------------|-------------------------------|
| :hourglass:         | Developing                    |
| :x:                 | Not started                   |
| :pause_button:      | Started but currently stopped |

(completed features will be moved to [Currently Implemented Features](#currently-implemented-features))

### Language

- :x: A Better requirements system
- :x: Dictionaries
- :x: More advanced imports
- :x: Classes (via prototypes)
- :x: Async support (through a @require flag)
- :x: A standard library (though certain imports, like fs, would need an @require flag)
- :x: For loops
- :x: A REPL
- :pause_button: More builtins
  - :x: Builtin Functions
  - :pause_button: Builtin Methods
    - :pause_button: Array methods
- :pause_button: Dynamic modules

### App

- :x: Tests

## Build

### Prerequisites

- [Rust](https://rust-lang.org/)
- The [uv](https://docs.astral.sh/uv/) package manager (will also auto-install the correct Python version for this project)

### Steps

Clone the repo:

```bash
git clone https://github.com/DELOLCAT/omni_script
cd omni_script
```

Run `build.py` with `uv`:

```bash
uv run build.py
```

The output would be stored in `dist/`
