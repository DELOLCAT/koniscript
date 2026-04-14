# The Platform File Specification (tentative)

This document describes how **platform files** will work in a future version of OmniScript (v0.2.0 or v0.3.0).

This is the second revision of this document.

## What are Platform Files

Platform Files will be a way to port OmniScript to a new runtime. They will describe where functions and runtime values will live, describe macros that can output completely custom bytecode, and also requirements.

In other words, Platform Files are basically a blueprint for the compiler.

## Syntax

Here is some self-describing syntax

```omp
@ver 1 # These are explained in the section `Version System`
func foo(1) 13 # A function with one argument, living at index 13 in the builtin pool
func bar(1, 3) # A function with 1 to 3 arguments, auto-incremented to 14
@ver 2
func baz(1, .) 16 # A function with 1 or more arguments at 16
func qux(., 5) # A function with up to 5 arguments
func quux(1) requires corge # A function which requires corge to work
run grault 18 # A runtime value (similar to _name), which can perhaps change during runtime, at index 18
attr garply(1) on str # A method for strings with one argument (syntax tentative)
@ver 3
attr waldo on str # An attribute for strings (syntax tentative)
# The macro syntax isn't developed yet 
```

These rules will be stored in `.omp` files, and imported through `@platform <name>`. Note that these files have no implementation, just definitions.

These can also be imported using a standard import, like `import std::random`, so that you can have FFI libraries that are just defined via platform files. They would be used as regular modules.

The search paths will be the same as modules.

Once the type-checker will be unveiled (Typescript-like), these will also support types.

## Version System

While the syntax hasn't been decided yet, here is how the versioning of these files will work:

There will be 3 numbers: a file version, feature versions, and a used version.

A set of symbols will get a feature version. For instance, lets say that in the example [here](#syntax), the first 2 functions (`foo` and `bar`) will get a feature version of 1, the next 2 get 2, and so on. Note that the version and blocks will get decorated with a syntax similar to `@ver <num>`.

The whole file will get a number as well, say 2.

The compiler will parse the platform file, and see which items have been used. For instance, let's say we only used `foo` and `bar`. Since those have a number of `1`, the compiler will output a used version of `1`. On the other hand, if we also use `baz`, the compiler will output a used version of `2`, which will be found out with `max(<used versions>)`.

When someone adds an item to the platform file, all what will happen is that they will decorate that new item with an ***incremented feature version***.

When someone **removes**, the whole platform file's version will get incremented.

The runtime will receive the file version and used version. It will check if the file version is **equal to** it's stored supported version, and will check if the used version is **less than or equal to** it's stored version.

The runtime would receive this structure (tentative):

``` omc
.platform
<name>.<file_version>.<used_version>
```

A practical example would be:

```omc
.platform
prelude.1.4
arduino.3.2
```

(see [the next section](#refactors) for more info on `prelude`)

If the runtime sees a platform or a version number it doesn't support, it will crash in a very similar fashion to how unsupported requirements crash. The VM will also emit an error code of `13` (CompatibilityError)

The compiler will also detect env clashes (ex. `prelude` defines a function at idx `5`, but `arduino` also does the same)

## Refactors

There really is going to be one refactor, and it's for the good, which is replacing the hardcoded indexes for the prelude (`println()`, `input()`, etc.) to a platform file.

In order to disable the `prelude.omp` file, you will add `@nostd` to your script.

As of now, the `prelude` file will reserve indexes from 0 to 30.
