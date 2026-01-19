# Ray: Write once, run wherever you want

Ray is a dynamic programming language that focuses on these main features:

- A simple VM (RayVM) that you could implement almost anywhere - even in Scratch mods
- Readability of code
- Ease of packaging (code compiles down to a single .rvm bytecode file)
- Compatibility: Supports @require flags (ex. @require fs, gui) so Ray can work smoothly across multiple runtime environments. This system is indev, so expect better features in the near future.

## Roadmap

| Icon               | Meaning      |
|--------------------|--------------|
| :white_check_mark: | Completed    |
| :hourglass:        | Finished     |
| :x:                | Not started  |

- :x: A Better requirements system
- :x: Dictionaries
- :x: More advanced imports
- :x: Classes (via prototypes)
- :x: Async support (through a @require flag)
- :x: A standard library (though certain imports, like fs, would need an @require flag)
- :x: For loops
- :x: A REPL
- :white_check_mark: The requirements syntax
