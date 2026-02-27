This is an update which mainly fixes #2, but also makes the CLI output better for CI on compiling. The VM is also not bundled into the compiler, so using `omni run` will search for a VM.

In Depth:

- Adds the `DUP` instruction
- Changes a lot of references to be a `Rc<Value>` in Rust instead of a `Value`
- Removes the menu that comes on `omni compile`
- Makes the file output to be a `.omc` file
