<!-- TODO -->
# Compiler and VM Errors in OmniScript

This document describes the errors that can be raised by the compiler and VM in OmniScript.

## Compiler Errors

This section is for errors raised by the compiler (`omni`)

### 1: Unterminated string literal

Used when a string doesn't terminate (end)

```omniscript
print('this string never ends)
```

### 2: Unexpected Character

Used when the tokenizer reaches a character that isn't even used in OmniScript

```omniscript
ifa 5 == 5 {
# ^
    print('What did you expect?')
}
```

### 3. Unexpected Token

Used when the parser reaches a token that is unexpected depending on the situation

```omniscript
if {
#  ^ the `LBRACE` token is unexpected

}
```

### 4. Expected identifier after `.`

Used when an identifier isn't used after a `.` (attribute)

```omniscript
a = 'hi'
a.
```

or

```omniscript
a = 'hi'
a.2
```

### 5. Cannot export anything other than an assignment or function

Used when you attempt to export anything other than an assignment or function:

```omniscript
export "foo"
```

### 6. Module not found

Used when the compiler can't find an imported module

```omniscript
import foo # But `foo` doesn't exist, or is put in a place where the compiler can't find it
```

### 7. Cannot have a non-optional argument after an optional argument

Used when you use a regular argument after an optional argument:

```omniscript
func foo(a='bar', b) {
    # ...
}
```

### 8. No source

Used when the compiler is told to include source info, but doesn't receive it (internal)

### 9. Variable not declared

Used when you use a variable (or function) before declaring it

```omniscript
print(a) # But a was never declared (a='foo' was never ran)
```

### 11. Invalid arg count (10 was removed)

Used when you provide too less or too many arguments to a function:

```omniscript
func foo() { # No arguments

}

foo('bar') # <- Expected exactly 0 arguments, got 1
```

or

```omniscript
func foo(bar='baz') {

}

foo('bar', 'baz') # <- Expected 0 to 1 arguments, got 2
```

### 12. Attribute not found

Used when you use an attribute that doesn't exist:

```omniscript
'hi'.non_existent() <- Could not find attribute non_existent:
```

### 13. Internal Error

An internal error. Should not be raised under any circumstance. Report immediately  

### 14. Attempted using a requirement where it isn't allowed

Used when you try to use a feature when you explicitly stated you won't:

```omniscript
@require types.arrays {
    # ...
} else {
    print(['foo', 'bar']) # <- Attempted using a(n) Array when it requires `types.arrays` in an illegal area
}
```

### 15. Break outside of loops

Used when you use `break` outside of a loop:

```omniscript
println('This isn\'t a loop')
break # <-
```
