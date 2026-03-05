from dataclasses import dataclass
import shutil
from typing import Generator
import typer
import os
import sys
from pathlib import Path
from omni_script.main import (
    Tokenizer,
    Parser,
    EOF,
    Token,
    Program,
    Compiler,
    CompilationException,
)
from omni_script import base_env
import copy
import tempfile
import subprocess
from rich import print
from rich.markup import escape
from rich.console import Console
from time import perf_counter

app = typer.Typer()

console = Console()

tracebacks = os.environ.get('OMNI_TRACEBACKS')


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


@dataclass
class CompilationResult:
    pass


@dataclass
class Failed(CompilationResult):
    compiler: None | Compiler
    exception: CompilationException


@dataclass
class Success(CompilationResult):
    instructions: list[str]

def get_program(file_content):
        try:
            current_env = copy.copy(base_env.compiler_env)
            tknr = Tokenizer(file_content)
            tkns: list[Token] = []
            while True:
                tkn = tknr.get_next_token()
                tkns.append(tkn)
                if tkn.type == EOF:
                    break
            psr: Parser = Parser(tkns, base_env.ASTenv)
            program: Program = psr.program()
            return program, current_env
        except CompilationException as e:
            return Failed(None, e)

def comp(
    file_content: str, filepath, features=None
) -> Generator[Compiler.Warn | Compiler.ModuleRequest, Program, CompilationResult]:

    if features is None:
        features = []
    
    tmp = get_program(file_content)
    
    if isinstance(tmp, Failed):
        return tmp
    
    program, current_env = tmp
    
    compiler = Compiler(current_env, base_env.ASTenv, base_env.attrs, str(filepath))
    
    try:
        cmp = compiler.compile(program, features, file_content)
    except CompilationException as e:
        return Failed(compiler, e)
    result = None
    while True:
        try:
            a = cmp.send(result)
            if isinstance(a, Compiler.ModuleRequest):
                if (Path(filepath).parent / (a.name + '.om')).is_file():
                    fp = Path(filepath).parent / (a.name + '.om')
                elif (Path(filepath).parent / 'packages' / (a.name + '.om')).is_file():
                    fp = (Path(filepath).parent / 'packages' / (a.name + '.om'))
                else:
                    raise NotImplementedError #TODO
                content = fp.read_text()
                tmp = get_program(content)
                if isinstance(tmp, Failed):
                    return tmp
                import_program, import_env = tmp
                result = Compiler.ModuleReceived(import_program, str(fp), content)
                                
            else:
                result = None
                yield a
        except StopIteration as e:
            return Success(e.value)
        except CompilationException as e:
            return Failed(compiler, e)


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
    file_content = Path(filepath).read_text()
    start_time = perf_counter()
    it = iter(comp(file_content, filepath, comp_features))

    instructions = None
    warns = 0
    while True:
        try:
            value = next(it)
            if isinstance(value, Compiler.Warn):
                warns+=1
                show_err_or_warn(value, filepath, file_content)
        except StopIteration as e:
            if isinstance(e.value, Success):
                instructions = e.value.instructions
                break
            elif isinstance(e.value, Failed):
                if tracebacks:  # To show Python tracebacks for development
                    raise e.value.exception
                show_err_or_warn(e.value, filepath, file_content)
                if warns > 0:
                    print(f'[red b]Failed in {round(perf_counter() - start_time, 3)} seconds, [yellow b]{warns} warnings emitted')
                else:
                    print(f'[red b]Failed in {round(perf_counter() - start_time, 3)} seconds')
                return
            else:
                raise
    fp = f'{str(filepath).removesuffix(".om")}.omc'
    if warns > 0:
        print(f'[green]Compiled in {round(perf_counter() - start_time, 3)} seconds, [yellow b]{warns} warnings emitted')
    else:
        print(f'[green]Compiled in {round(perf_counter() - start_time, 3)} seconds')
    status = console.status(f'Writing to {fp}')
    status.start()
    with open(fp, 'w') as file:
        file.write('\n'.join([str(x) for x in instructions]))
    status.stop()
    print(f'Wrote to {fp}')


def show_err_or_warn(e: Failed | Compiler.Warn, filepath, file_content: str):
    if isinstance(e, Failed):
        color = '[red b]'
        tag = f'[red b]E{e.exception.code:02}'
        ln = e.exception.line
        col = e.exception.col
        msg = e.exception.msg
    else:
        color = '[yellow b]'
        tag = '[yellow b]Warning'
        col = e.col
        ln = e.line
        msg = e.message
    print()
    print(f'{tag}: {msg}:', file=sys.stderr)
    print(
        f'at {filepath}{"[green]:" + str(ln + 1) if ln is not None else " [red]No line data available"}{":" + str(col) if col is not None else ""}',
        file=sys.stderr,
    )
    if ln is not None:
        splitted = file_content.splitlines()
        from_lines = max(0, min(ln - 3, len(splitted)))
        to_lines = max(0, min(ln + 4, len(splitted)))
        for i, cln in enumerate(splitted[from_lines:to_lines], from_lines + 1):
            arr = f'{color}->    [/]' if ln == i - 1 else '      '
            print(f'{arr}[blue dim]{i} | [/]{escape(cln)}', file=sys.stderr)


@app.command()
def run(
    filepath: Path,
):
    # run() should always compile with debug info enabled
    # ignore release/line/source choices and force both 'source' and 'line'
    comp_features: list[str] = ['source', 'line']

    file_content = Path(filepath).read_text()
    it = iter(comp(file_content, filepath, comp_features))
    instructions = None
    while True:
        try:
            value = next(it)
            if isinstance(value, Compiler.Warn):
                show_err_or_warn(value, filepath, file_content)
        except StopIteration as e:
            if isinstance(e.value, Success):
                instructions = e.value.instructions
                break
            elif isinstance(e.value, Failed): # `elif` for IDE type recognition
                if tracebacks:
                    raise
                show_err_or_warn(e.value, filepath, file_content)
                exit(1) # Abort
            else:
                raise # Impossible

    f = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.omc')
    try:
        f.write('\n'.join([str(x) for x in instructions]))
        # We need to close the file so that the subprocess can open it.
        f.close()
        vm_path = shutil.which('omvm')
        if (Path(__file__).parent / exec_name('omvm')).is_file():
            vm_path = Path(__file__).parent / exec_name('omvm')
        elif vm_path is not None:
            pass
        else:
            print(
                '[red b]Could not find `omvm` (OmniVM), which is required to run programs'
            )
            sys.exit(127)
        # run the VM and capture its output for tests, but also echo to user
        out = subprocess.run([str(vm_path), 'run', f.name], capture_output=True)
    finally:
        os.unlink(f.name)

    # print VM output when invoked as a CLI command
    if out.stdout:
        sys.stdout.buffer.write(out.stdout)
    if out.stderr:
        sys.stderr.buffer.write(out.stderr)
    # propagate exit code
    if out.returncode != 0:
        sys.exit(out.returncode)

    return out  # For tests


if __name__ == '__main__':
    app()
