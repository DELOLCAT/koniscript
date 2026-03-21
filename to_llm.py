"""
This is a simple tool I made so that you can send file contents with line numbers to LLMs.
This is purely to **FIND BUGS** and is **NOT** intended to generate code.
AI can be great for assisting software development, but should **NOT** be used to completely replace a human.
"""
import sys
from rich import print
from pathlib import Path
from pyperclip import copy
if len(sys.argv) > 1:
    filepath = Path(sys.argv[1]).resolve()
else:
    try:
        from questionary import path
        q = path('What is the filepath?')
        filepath = Path(q.ask()).resolve()
    except ImportError:
        print('[b red]Questionary not installed, use `uv sync --extra dev` for autocomplete on paths')
        filepath = Path(input("What is the filepath?\n>>> "))


if not filepath.is_file():
    print(f'[b red]{filepath} is not a file')
    exit(1)

text = filepath.read_text().splitlines()
out = []
for i, item in enumerate(text, 1):
    out.append(str(i) + ' | ' + item)

copy('\n'.join(out))
print("[green b]Copied output")
