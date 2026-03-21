# OmniScript: Write once, run wherever you want

## NOTICE: OmniScript is still indev, expect breaking changes

For contributing, see [CONTRIBUTING.md](CONTRIBUTING.md)

OmniScript is a dynamic programming language that focuses on these main features:

- A ridiculously simple stack based VM (OmniVM) that you could implement almost anywhere - even in Scratch mods (currently only 19 instructions)
- Readability of code
- Ease of packaging (code compiles down to a single .omc bytecode file)
- Compatibility: Supports @require flags (ex. @require fs, gui) so OmniScript can work smoothly across multiple runtime environments. This system is indev, so expect better features in the near future. This also means that runtimes can be even smaller, and also on embedded systems.

## Currently implemented features

- Variables
- Functions
- Basic builtins (print, input, to_(type))
- Arrays (methods indev)
- The requirements syntax
- Stack traces
- Optional function arguments

## Usage

### Writing a program

Since OmniScript is still in early development, there aren't many features.

- Types: `'string'`, integer: `2`, float: `3.14`, and booleans `true`/`false`
- Functions: `name(args)`
- Comments (multi-line soon): `# I am a comment`

Example:

```omniscript
print('foo, bar', ' baz') # The print function takes multiple arguments, and concatenates them (without a space)
```

- Variables:

```omniscript
this_is_a_var = 'foo'
print(this_is_a_var)
```

- Arithmetic:

```omniscript
print(5 + 5 / 2)
```

- Conditionals:

```omniscript
num = input('Enter a number\n>>> ') # The input function prints a message and waits for user input, returning the input given by the user.

print(num == 5)
if num == 5 {
  print('The number is equal to 5')
} else if num == 10 {
  print('The number is equal to 10')
} else {
  print('The number is not equal to 5 or 10')
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

- Requirements:
```omniscript
@require strings.methods, attributes # A bare require statement will cause the VM to exit when starting to execute.
print('hi'.upper())

@require types.arrays {
  arr = []
  arr.push('test')
} else {
  print('Arrays not supported') # Any code that tries to use arrays in here will fail to compile
}
```
- Imports:
main.om
```omniscript
import some_mod
print(some_mod.hi())
```
some_mod.om
```omniscript
export func hi() {
  print('Hello from some_mod!'
  return 'some value'
```

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

View GithubMilestones (currently [v0.1.0](https://github.com/DELOLCAT/OmniScript/milestone/1)) to see progress

(completed features will be moved to [Currently Implemented Features](#currently-implemented-features))

v0.1.0

- A Better requirements system
- Better compiler error messages
- More advanced imports
- For loops

v0.2.0

- Dynamic modules
- Dictionaries
- A better standard library (though certain imports, like fs, would need an @require flag)
- An (optional for max compatibility) binary bytecode format

v0.3.0

- Classes (via prototypes)
- A REPL
- Async support (through an @require flag)

## Build

### Prerequisites

- [Rust](https://rust-lang.org/)
- The [uv](https://docs.astral.sh/uv/) package manager (will also auto-install the correct Python version for this project)

### Steps

Clone the repo:

```bash
git clone https://github.com/DELOLCAT/OmniScript.git
cd OmniScript
```

Run `build.py` with `uv`:

```bash
uv run build.py
```

The output would be stored in `dist/`
