# The koniscript Runtime

## Note that this spec is NOT stable, and NOT complete

## Architecture

The VM uses a LIFO stack, with each item being a tag and value. The tag signifies the type of the item, like a `string`, encoded as an integer.

### Types and their Tags

Tag | Type
----|----
1   | Integer
2   | String
3   | Boolean
4   | Function
5   | Builtin (compiler use, NEVER appears in runtime)
6   | Null
7   | Float
8   | Module
9   | Array

## Instructions

- `JMP int`: Jumps to an instruction at bytecode offset `int`
- `JMPIF int`: Pops an item from the stack, and jumps to bytecode offset `int` if it is true
- `JMPIFF int`: Pops an item from the stack, and jumps to bytecode offset `int` if it is false

TODO: this