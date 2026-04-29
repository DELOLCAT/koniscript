   <!-- markdownlint-disable MD033 MD041 -->
<div align='center'>
<img src='icons/full.svg' alt='koniscript logo'><br/>
Simple · Readable · Cross-Platform · Dynamic
</div>

---

⚠️ **NOTICE: koniscript is still in early development, expect breaking changes**

---

## AI Policy

If you don't plan on contributing, continue to the [next heading](#about).

I am quite strict about AI use in programming. I have supplied a `GEMINI.md` file (you can rename to `agents.md`) for agents, as they can be quite useful for finding the origin of a bug, reviewing code, suggesting enhancements, and also writing tests. I've also added `sourcery-ai` to this repo, as it's code reviews can also be nice.

However, I do NOT like using AI for anything more than above. If a PR is LLM generated, or violates any of the guidelines above, it would get discarded (although any ideas it created may be considered).

See [CONTRIBUTING.md](CONTRIBUTING.md) for more info

## About

koniscript is a dynamic programming language that focuses on these main features:

- A ridiculously simple stack based VM (konivm, shortened to `kovm`) that you could implement almost anywhere - even in Scratch mods. The instruction set only has 14 required instructions, and 7 optional ones (managed through [`@require` flags](#compat))
- Readability of code
- Single file packaging - code compiles down to a single .knc bytecode file
- <a id='compat'>@require flags (ex. `@require fs, gui`, see the [syntax example](#writing-a-program) for more) so koniscript can work smoothly across multiple runtime environments. This also means that runtimes can be even smaller, and also on embedded systems.

## Usage

### Writing a program

- Types: `'string'`, integer: `2`, float: `3.14`, and booleans `true`/`false`
- Function calls: `name(args)`
- Comments (multi-line soon): `# I am a comment`

For example, using the above:

```koniscript
println('foo, bar', 'baz') # The println function takes multiple arguments, and concatenates them with a space
```

- Variables:

```koniscript
this_is_a_var = 'foo'
println(this_is_a_var)
```

- Arithmetic:

```koniscript
println(5 + 5 / 2)
```

- Conditionals:

```koniscript
num = input('Enter a number\n>>> ') # The input function prints a message and waits for user input, returning the input given by the user.

println(num == 5)
if num == 5 {
  println('The number is equal to 5')
} else if num == 10 {
  println('The number is equal to 10')
} else {
  println('The number is not equal to 5 or 10')
}
```

- While loops

```koniscript
i = 0
while i < 5 {
  println(i)
  i+=1
}
```

The `break` keyword is also supported

- Functions (and recursion):

```koniscript
func fib(n) {
  if n <= 1 {
    return n
  }
  return fib(n - 1) + fib(n - 2)
}

println(fib(10)) # => 55
```

Functions are also first class

```koniscript
func run_with_message(f) {
  println('Running...')
  val = f() # Note that this will raise a warning, as the compiler can't check the number of arguments. This will be fixed when the type checker is released.
  println('Completed!')
  return val
}

func some_callback() {
  print('Hello from the inner callback!')
}

run_with_message(some_callback)
```

- Requirements:

```koniscript
@require strings.methods, attributes # A bare require statement will cause the VM to exit when starting to execute.
println('hi'.upper())

@require types.arrays {
  arr = []
  arr.push('test')
} else {
  println('Arrays not supported') # Any code that tries to use arrays in here will fail to compile
}

@require indexes # All bare require statements are collected. This whole program will fail on launch if the runtime doesn't support indexes
# ...
```

Note that using a feature that is under a requirement will implicitly add the requirement and raise a warning, telling you to make it explicit.

- Arrays:

```koniscript
@require types.arrays

a = [
  'foo',
  'bar'
]

println(a[0]) # => foo

a.push('baz')

println(a) # => ['foo', 'bar', 'baz']
```

- Dictionaries (indev)

```koniscript
@require types.dicts

a = %{
  'foo': 'bar',
  'baz': 5,
  5: 'boo'
}

println(a['foo']) # => bar
println(a.foo) # => bar

println(a.baz) # => 5
```

- Imports:

main.kn

```koniscript
import some_mod
println(some_mod.hi())
```

some_mod.kn

```koniscript
export func hi() {
  println('Hello from some_mod!')
  return 'some value'
}
```

- Runtime values:

```koniscript
@require runtime_values # Note that runtime values can change during runtime, thus they may be too complex for some runtimes to implement
func main() {
  println('Hello from my program')
}

if _name == '[main]' {
  main()
}
```

### CLI

To run a program, use `koni run`:

```bash
$ koni run examples/fib.kn 
55
```

To compile a program, use `koni compile`:

```bash
$ koni compile examples/fib.kn
Compiling with debug (source+line info). See `koni compile --help` for more info
Wrote to examples/fib.knc
```

To run compiled programs, use `kvm run`:

```bash
$ kvm run ./examples/fib.knc
55
```

## Roadmap

View GitHub Milestones (currently [v0.1.0](https://github.com/DELOLCAT/koniscript/milestone/1)) to see the full roadmap with versions and progress.

Here are some features that are planned in the future:

### Platform Files

A cross-platform, language agnostic, simple way for FFI, with a smart but simple versioning system (yes, I'm proud of that); see the [full spec](specs/future/platform_files.md) for more.

### A type checker

Not much to write here, it'll just be a type checker similar to TypeScript.

### Airport

A platform manager focusing on DX. Full spec to be written

## Build

### Prerequisites

- [Rust](https://rust-lang.org/)
- The [uv](https://docs.astral.sh/uv/) package manager (will also auto-install the correct Python version for this project)

### Steps

Clone the repo:

```bash
git clone https://github.com/DELOLCAT/koniscript.git
cd koniscript
```

Run `build.py` with `uv`:

```bash
uv run build.py
```

The output would be stored in `dist/`
