# Contributing Guidelines

Nobody has contributed to this project yet, but this document is here just in case.

## Details Regarding AI Usage

<!-- NOTE: if you update this, don't forget to update the rules in README.md -->

I am quite strict about AI use in programming. I have supplied a `GEMINI.md` file (you can rename to `agents.md` for support with other tools) for agents, as they can be quite useful for finding the origin of a bug, reviewing code, suggesting enhancements, and also writing tests. I've also added `sourcery-ai` to this repo, as its code reviews can also be nice.

However, I do NOT like using AI for anything more than above. If a PR is LLM generated, or violates any of the guidelines above, it would get discarded, although any ideas it created may be considered. Anybody can type out prompts - that's not useful, but everybody can't review code that clearly has low quality, not aligned with goals, or are created by people that don't even know how the code works.

## Getting started

First, create a fork of the repo. You can clone it with

```sh
git clone https://github.com/DELOLCAT/koniscript.git
```

Also run `uv sync` to install all dependencies and the correct Python version

The repo has this structure:

- `/src/koni_compiler` contains the compiler, written in Python. This is what converts source code to output bytecode
- `/kovm` contains the VM (also referred to as the *runtime*), written in Rust. This is what *runs* the output bytecode
- `/koni_lsp` contains a small LSP server. This is used in IDEs to show errors, warnings, and also syntax highlighting
- `/` (the root) contains dev scripts, Pyinstaller configs, and other repo files. The root files are listed below:

```tree
bench.py           -> A simple script that runs a command 10 times and saves the amount of time it took to run for each call, and the average  
build.py           -|
build_nuitka.py     | Build scripts, used to build the executables for the compiler and VM.
build_vm.py        -|
CONTRIBUTING.md    -> The contributing guidelines document you are reading right now
devvm              -> A shell script that runs the VM with the supplied arguments. Used with `./devvm run path/to/output.knc` or other VM commands
GEMINI.md          -> A file that agents read to understand the layout and goals of the project. You may rename this to `agents.md` for use with other agents
LICENSE            -> The MIT license for this project
pyproject.toml     -> The Python environment settings. Remember to use uv for a good experience with this project
README.md          -> The README document that appears on the repo's homepage
RELEASE_BODY.md    -| A file that is used to change the body of a release created by the GitHub action. Not used anymore, instead the draft
RELEASE_TITLE.txt  -| that the action creates is edited
to_llm.py          -> A script that appends line numbers to a file so you can paste it into an LLM
unix.spec          -> The Pyinstaller spec file that is used for UNIX-like environments, like Linux or macOS.
uv.lock            -> uv's lock file, you don't have to edit this
win.spec           -> The PyInstaller spec file that is used for Windows
```

Also the directories are listed below:

```tree
examples/          -> Contains example scripts
icons/             -> Contains the koniscript logos (mini and full)
koni_lsp/          -> Contains the LSP server and editor extensions
kovm/              -> Contains the Rust bytecode VM
packages/          -> A directory that is part of koniscript's search path for modules. Mainly for testing purposes
specs/             -> Contains documentation and specifications
src/koni_compiler  -> Contains the Python compiler
tests/             -> Contains `pytest` tests
```

Whenever you are editing Python files, remember to use `uv` instead of `python3` or `conda`, as this project is designed to be used with uv.

This project also has `tmp/` in its `.gitignore` file, so you can put temporary testing scripts into any folder named `tmp/`, and they won't be included in Git  

Use `uv run test` to run tests

## Issue tracker

Issues can be submitted with [GitHub Issues](https://github.com/DELOLCAT/koniscript/issues/). Despite the name, issues are also the place for suggestions and feature requests.

I haven't made any templates, but here is one you can use:

Title: A short but informative title about ***what*** you want/plan on adding/removing/updating.
Body: A body paragraph that has all of the information. If it's a bug request, try to include any relevant information. If it's a feature, try to tell how you imagine it should work

For instance, a good issue would be:

````md
Break not working properly

The `break` keyword doesn't seem to work in this source code:

```koniscript
x = 0
while true {
    if x == 5 {
        break
    }
    x += 1
}
```

It gives me this stack trace:

<compiler or VM output here>
````

As the user didn't know ***why*** the issue happened (though the above isn't a real issue), they only said that the break keyword wasn't working

## Pull Requests

Pull requests (shortened to PRs) are how you submit code that you have made or are working on.

Draft PRs should be made for code that you are still working on.

Regular PRs should be made for code you have already completed (although if it would take more than 30 minutes to make the changes, draft PRs are recommended)

PRs should be made for an issue. If you haven't made an issue for the change you are going to make, make an issue, unless if it is anything trivial, like a typo.

Also wait for an issue you've made to be discussed and approved, to ensure that the community ***wants*** your feature in the code, or if the bugfix you're making is actually intentional behavior.

For draft PRs, it is recommended to make a checklist. GitHub uses GFM (GitHub Flavoured Markdown), which supports this syntax for checklists:

```md
- [ ] Unchecked checkbox
- [x] Checked checkbox
```

After you set a checkbox in the body, you can click on them to check/uncheck them.

Another thing that is recommended for PRs is to use [closing keywords](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests) to an issue that requested the feature/bug fix that you are implementing.

Here's an example of a draft PR:

```md
Implement dictionaries

Closes #19

I have also decided to add methods like `_str` that builtins can use

Checklist:

- [ ] Add the `DICT_START` token
- [ ] Add the `KoniDict` AST node and make the parser output it
- [ ] Add support for `KoniDict` in the compiler
- [ ] Add methods for builtins accessible via `_str` or similar on dicts
    - [ ] Add `_str`
    - [ ] Add `_repr`
    - [ ] Add `_type_display`
    - [ ] Add `_int`
    - [ ] Add `_len`
```

Regular PRs could look like this:

```md
Fix typo in README.md

Not much, just changes the word "fooo" to "foo"
```
