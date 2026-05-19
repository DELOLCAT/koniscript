# Compiler/VM Errors and Warnings in koniscript

This document describes the errors and warnings that can be raised by the compiler and VM in koniscript.

## Compiler Errors

This section is for errors raised by the compiler (`koni`)

### 1: Unterminated string literal

Used when a string doesn't terminate (end)

```koniscript
print('this string never ends)
```

### 2: Unexpected Character

Used when the tokenizer reaches a character that isn't even used in koniscript

```koniscript
ifa 5 == 5 {
# ^
    print('What did you expect?')
}
```

### 3: Unexpected Token

Used when the parser reaches a token that is unexpected depending on the situation

```koniscript
if {
#  ^ the `LBRACE` token is unexpected

}
```

### 4: Expected identifier after `.`

Used when an identifier isn't used after a `.` (attribute)

```koniscript
let a = 'hi'
a.
```

or

```koniscript
let a = 'hi'
a.2
```

### 5: Cannot export anything other than an assignment or function

Used when you attempt to export anything other than a declaration or function:

```koniscript
export "foo"
```

or when you try to export an empty declaration:

```koniscript
export let foo
```

### 6: Module not found

Used when the compiler can't find an imported module

```koniscript
import foo # But `foo` doesn't exist, or is put in a place where the compiler can't find it
```

### 7: Cannot have a non-optional argument after an optional argument

Used when you use a regular argument after an optional argument:

```koniscript
func foo(a='bar', b) {
    # ...
}
```

### 8: No source

Used when the compiler is told to include source info, but doesn't receive it (internal)

### 9: Variable not declared

Used when you use a variable (or function) before declaring it

```koniscript
print(a) # But a was never declared (`let a='foo'` was never ran)
```

or

```koniscript
foo = 'bar' # But you never declared foo with `let foo`
```

### 11: Invalid arg count (10 was removed)

Used when you provide too less or too many arguments to a function:

```koniscript
func foo() { # No arguments

}

foo('bar') # <- Expected exactly 0 arguments, got 1
```

or

```koniscript
func foo(bar='baz') { # Note that default arguments are very unstable, see [#34](https://github.com/DELOLCAT/koniscript/issues/34)

}

foo('bar', 'baz') # <- Expected 0 to 1 arguments, got 2
```

### 12: Attribute not found

Used when you use an attribute that doesn't exist:

```koniscript
'hi'.non_existent() <- Could not find attribute non_existent:
```

### 13: Internal Error

An internal error. Should not be raised under any circumstance. Report immediately  

### 14: Attempted using a requirement where it isn't allowed

Used when you try to use a feature when you explicitly stated you won't:

```koniscript
@require types.arrays {
    # ...
} else {
    print(['foo', 'bar']) # <- Attempted using a(n) Array when it requires `types.arrays` in an illegal area
}
```

### 15: Break outside of loops

Used when you use `break` outside of a loop:

```koniscript
println('This isn\'t a loop')
break # <-
```

### 16: Unterminated closing brace in format string

Used when you forget to add a closing brace (`}`) in a format string

```koniscript
println(`This format literal has no ${closing brace`)
```

### 17: Invalid escape sequence

Used when you use an invalid escape sequence in a string:

```koniscript
println('the escape sequence \g does not exist')
```

### 18: Invalid assignment target

Used when you try to assign a value to something that cannot be assigned to:

```koniscript
'foo' = 'bar'
```

### 19: Attempted to divide by 0

Used when the compiler finds an area where you attempt to divide by 0 (at the moment this is done during constant folding):

```koniscript
println(5 / 0)
```

### 20: Attempted to multiply a string by a negative number

Used when the compiler finds an area where you attempt to multiply a string by a negative number (at the moment this is done during constant folding):

```koniscript
println('*' * -2)
```

### 21: Value cannot be constant folded

Used when you use a value that cannot be embedded in the constant pool in a constant value:

```koniscript
const foo = [] # Arrays cannot be constant folded
```

Note that koniscript constant folds these values, so:

```koniscript
const foo = 2 * 2
```

will work

## Compiler Warnings

### 1: Requirement Implicitly added

Used when you use a feature that needs a requirement not added.

```koniscript
let a = ['foo'] # arrays need the types.arrays requirement
a.push('bar')
println(a)
println('Completed!')
```

There are 2 fixes:

- add `@require <req>` to the __top__ of your script (note that bare requires get collected into one, thus it doesn't matter where they are). This means that your whole script will refuse to start on runtimes without that requirement:

```diff
+ @require types.arrays
  let a = ['foo'] # arrays need the types.arrays requirement
  a.push('bar')
  println(a)
  println('Completed!')
```

- wrap the statement and related statements into an `@require` block, optionally with an `else` fallback. Use this if your program doesn't use that requirement as a core part of the way it works

```diff
+ @require types.arrays {
      let a = ['foo'] # arrays need the types.arrays requirement
      a.push('bar')
      println(a)
+ } else {
      println('Arrays are not supported')
+ }

  println('Completed!')
```

### 2: Format string with no expressions

Used when you have a format string without any expressions:

```koniscript
println(`this is a format string`)
```

To fix, replace the format string with a regular string char, like `'` or `"`. Note that using a format string with no expressions has no performance impact

### 3: Unreachable blocks

Used when a block is unreachable:

```koniscript
if false {
    println('idk what to type anymore')
}
```

To fix, remove the block

### 4: Redundant if statements

Used when you have an if statement that always runs:

```koniscript
if true {
    println('windows sucks')
}
```

To fix:

- Move the statements outside of the if statement:

```diff
- if true {
      println('windows sucks')
- }
```

- Move the statements to their own block, if anything inside needs to be separated from the outside scope:

```diff
- if true {
+ {
      println('windows sucks')
  }
```

### 99: Type checker missing warnings

These warnings come up because koniscript has no type checker, so it warns you on things that it cannot check:

```koniscript
func run_with_message(task, fn) {
    println(`Starting task ${task}...`)
    fn() # <- Could not detect how many min and max arguments for function call
    println(`Finished task ${task}!)
}
```

As development on the type checker is right after writing this section of this document (at the time of writing, warning codes have just been added), these warnings are temporary, and there aren't many examples

## Runtime (VM) errors

This section is for errors raised by the runtime (`kovm`)

### 1: InvalidArgCount

Used when you supply an invalid number of arguments to a function:

```koniscript
func foo(bar) {
    # ...
}
let a = foo
a() # <- 0 arguments, and the compiler cannot catch this as of now
```

### 2: ConversionNotPossible

Used when types cannot be casted no matter what:

```koniscript
func foo() {
    # ...
}
println(to_int(foo)) # <- Functions can't be converted to integers
```

### 3: ConversionFailed

Used when types can be casted, but failed:

```koniscript
println(to_int('foo')) # <- Strings can be casted, but this isn't a valid int
```

### 4: IoError

Used when the runtime experiences an error with IO, like failing to flush standard output (note that the runtime hasn't implemented this for regular `println` yet): <!--TODO: add regular `println` support -->

```koniscript
print('hello') # But this script has been ran in a pipe that has closed
```

### 5: Invalid Bytecode

Used when the runtime finds an invalid instruction. Should *__NOT__* be raised normally:

(note that the following is compiled):

```omc
JMP
```

As you can see above, there is no target to jump to

### 6: Variable Not Found

Used when the runtime reaches a variable that hasn't been declared in the current scope. Note that the compiler would prevent this from happening.

```koniscript
println(foo) # The compiler somehow didn't catch that `foo` has never been declared
```

### 7: StackUnderflow

Used when the runtime attempts to pop the stack, but it is empty. This should *__NOT__* be raised in normal circumstances, so this example is for compiled code:

```omc
PUSH_CONST 0
ADD
```

Above, the `ADD` instruction will attempt to pop 2 values, but only 1 was pushed

### 8: TypeError

Used when something expects a certain type, but got something else:

```koniscript
println(len(2)) # You cannot find the `len` of an `int`
```

### 9: FuncNameStr

Used when a function with a non-string name is found. This should *__NOT__* be raised in normal circumstances. For instance, if the name is stored in the constant pool at `2` and the runtime finds an `int` instead of a `str`, this error would be raised.

### 10: InvalidLocal

Used when a variable is fetched with an invalid local index. This should *__NOT__* be raised in normal circumstances (although there is a known edge case, discussed [in this error](#6-variable-not-found)).

For instance, let's say that we have this variable table:

```none
Frame 0:
    0: string 'foo'
    1: int '5'
Frame 1:
    0: string 'bar'
```

And you attempt to fetch `1:1`. The second number is the local index, which, as you can see, there is only 1 local at `0`.

### 11: CompatibilityError

Used when the VM attempts to run code that requires a feature which it doesn't support, or uses a platform file (future, see the [Platform Files Specification](../future/platform_files.md)) that it doesn't support.

For instance, let's say that we have a program with this:

```koniscript
@require types.arrays

a = [
    'foo',
    'bar',
    'baz'
]
```

But, we're running on a very limited runtime. When the runtime opens the file, it will see

```omc
.reqs arrays
```

And completely stop, not even beginning the program

### 12: NoCode

Used when the runtime opens a file with no `.code` segment. This error should *__NOT__* be raised under normal circumstances, so this example is compiled:

```omc
.version
ENV 1
ISA 1
.frame 0 
.const
2;foo;
```

As you can see, above the `.code` segment was never started, which it usually would after `.const`.

### 13: ValueError (will be replaced by more descriptive errors)

Used when the runtime cannot find a value.

There is no example, as when this error code is raised is quite scattered and generic

### 14: AttributeError

Used when an attribute cannot be found for an item:

```koniscript
'foo'.bar() # <- The attribute `bar` doesn't exist
```

### 15: ExitSignal

Internal. Used when a builtin wants to make the VM exit. This may not exist in other implementations

### 16: InvalidOperation

Used when you do an operation that cannot be done:

```koniscript
[].pop() # <- Cannot `pop()` from an empty array
```

### 17: IndexError

Used when an index is out of range or doesn't exist:

```koniscript
a = []

a[0] # <- Index 0 out of range
```

### 18: MathError

Used during certain calculations when they are mathematically impossible or undefined:

```koniscript
println(5/0) # <- Attempted to divide by 0
```

### 19: OverflowError

Used whenever an integer overflows
