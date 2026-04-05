# The OmniScript Documentation (early dev)

## What is OmniScript?

OmniScript is a dynamic programming language, designed to run anywhere, while still being simple to read. OmniScript is still indev, so expect things to change.

## Architecture

At the moment, there are 2 main components:

- A *compiler*, written in Python for quick development. This compiles down code into a text-based bytecode (`.omc` file extension). Right before then v1.0 release, a binary bytecode format will also be released, with the format `.omb`. The text based bytecode will always be supported, as it allows OmniScript to run in places where binary operations aren't available (like TurboWarp). This bytecode will then be handed off to the *VM* to be executed. In the future, this will also have a TypeScript-like type checker.

- A *VM*, sometimes referred to as a *runtime*, will receive the bytecode and execute it. This is supposed to be simple, while still optionally having more advanced capabilities, done via a requirement system. In the future, there will also be [*Platform Files*](../future/platform_files.md), giving OmniScript FFI abilities in a predictable and language agonistic way.

<!-- TODO: write syntax examples -->