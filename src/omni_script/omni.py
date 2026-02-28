import shutil
import typer
import os
import sys
from pathlib import Path
from omni_script.main import Tokenizer, Parser, EOF, Token, Program, Compiler
from omni_script import base_env
import copy
import tempfile
import subprocess
from rich import print
from rich.console import Console

app = typer.Typer()

console = Console()


def exec_name(name: str) -> str:
    if sys.platform == 'win32':
        return name + '.exe'
    return name


def bundled_exe(name: str) -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    if sys.platform == 'win32':
        name += '.exe'
    return base / name


class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path


def comp(filepath: Path, features=None):
    if features is None:
        features = []
    current_env = copy.copy(base_env.compiler_env)  # noqa: F841
    file_content = Path(filepath).read_text()
    tknr = Tokenizer(file_content)
    tkns: list[Token] = []
    while True:
        tkn = tknr.get_next_token()
        tkns.append(tkn)
        if tkn.type == EOF:
            break
    psr: Parser = Parser(tkns, base_env.ASTenv)
    program: Program = psr.program()
    compiler = Compiler(current_env, base_env.ASTenv)
    cmp = compiler.compile(program, features, file_content)
    while True:
        try:
            yield next(cmp)
        except StopIteration as e:
            return e.value


@app.command()
def compile(
    filepath: Path,
    release: bool = typer.Option(
        False,
        '--release',
        '-r',
        is_flag=True,
        help='For turning off all debug features. Use when building the final output of your app',
    ),
    line: bool | None = typer.Option(
        None,
        '--line',
        '-l',
        is_flag=True,
        help='For adding line info into your app for stack traces. Default: TRUE',
    ),
    source: bool | None = typer.Option(
        None,
        '--source',
        '-s',
        is_flag=True,
        help='For adding a copy of the source into your app for stack traces. Default: TRUE',
    ),
):
    if release:
        comp_features = []
    elif not source and not line:
        comp_features = ['source', 'line']
    else:
        comp_features = []
        if source:
            comp_features.append('source')
        if line:
            comp_features.append('line')
    if len(comp_features) == 2:
        out = 'debug'
    elif len(comp_features) == 0:
        out = 'release'
    else:
        out = '+ '.join(comp_features) + ' info'
    print(
        f'Compiling with [b green]{out}[/]{" [d](source+line info)[/]" if out == "debug" else ""}. [blue]See `omni compile --help` for more info'
    )
    it = iter(comp(filepath, comp_features))

    instructions = None
    while True:
        try:
            value = next(it)
            if isinstance(value, Compiler.Warn):
                print(f'[yellow b]{value.message}')
        except StopIteration as e:
            instructions = e.value
            break
    fp = f'{str(filepath).removesuffix(".om")}.omc'
    status = console.status(f'Writing to {fp}')
    status.start()
    with open(fp, 'w') as file:
        file.write('\n'.join([str(x) for x in instructions]))
    status.stop()
    print(f'Wrote to {fp}')


@app.command()
def run(filepath: Path, debug: bool = False, features=[]):
    gen = comp(filepath)
    f = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.omc')
    try:
        # Consume the generator and capture its return value
        instructions = None
        try:
            while True:
                v = next(gen)
                if isinstance(v, Compiler.Warn):
                    print(f'[yellow b]{v.message}', file=sys.stdout)
        except StopIteration as e:
            instructions = e.value

        f.write('\n'.join([str(x) for x in instructions]))
        # We need to close the file so that the subprocess can open it.
        f.close()
        vm_path = shutil.which('omvm')
        if (Path(__file__) / 'omvm').is_file():
            vm_path = Path(__file__).parent / exec_name('omvm')
        elif vm_path is not None:
            pass
        else:
            print(
                '[red b]Could not find `omvm` (OmniVM), which is required to run programs'
            )
            sys.exit(127)
        out = subprocess.run([str(vm_path), 'run', f.name], capture_output=True)
    finally:
        os.unlink(f.name)
    return out # For tests

if __name__ == '__main__':
    app()
