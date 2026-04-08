from dataclasses import dataclass
import shutil
from typing import Generator
import typer
import os
import sys
from pathlib import Path
from colorama import init
from omni_compiler.main import (
    CompilerError,
    Tokenizer,
    Parser,
    EOF,
    Token,
    Program,
    Compiler,
    CompilationException,
)
from omni_compiler import base_env
import copy
import tempfile
import subprocess
from ansimarkup import ansiprint as print
from ansimarkup import raw
from time import perf_counter
init(True)
app = typer.Typer()


tracebacks = os.environ.get('OMNI_TRACEBACKS')


def exec_name(name: str) -> str:
    return f'{name}.exe' if sys.platform == 'win32' else name


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
    compiler: Compiler | None
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
                if (Path(filepath).parent / (f'{a.name}.om')).is_file():
                    fp = Path(filepath).parent / (f'{a.name}.om')
                elif (Path(filepath).parent / 'packages' / (f'{a.name}.om')).is_file():
                    fp = Path(filepath).parent / 'packages' / (f'{a.name}.om')
                else:
                    raise CompilerError(
                        6,
                        f'Could not resolve module `{a.name}`',
                        a.line,
                        a.col,
                        a.end_line,
                        a.end_col,
                        compiler.mod_stack[-1].fp,
                    )  # TODO: columns

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
):  # sourcery skip: low-code-quality
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
        f'Compiling with <b><green>{out}</green></b>{" <d>(source+line info)</d>" if out == "debug" else ""}. <blue>See `omni compile --help` for more info</blue>'
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
                warns += 1
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
                    print(
                        f'<b><red>Failed in {round(perf_counter() - start_time, 3)} seconds, </red><yellow>{warns} warnings emitted</yellow></b>'
                    )
                else:
                    print(
                        f'<red><b>Failed in {round(perf_counter() - start_time, 3)} seconds</b></red>'
                    )
                return
            else:
                raise
    fp = f'{str(filepath).removesuffix(".om")}.omc'
    if warns > 0:
        print(
            f'<green>Compiled in <b>{round(perf_counter() - start_time, 3)}</b> seconds, </green><yellow><b>{warns} warnings emitted</b></yellow>'
        )
    else:
        print(f'<green>Compiled in <b>{round(perf_counter() - start_time, 3)}</b> seconds</green>')
    with open(fp, 'w') as file:
        file.write('\n'.join([str(x) for x in instructions]))
    print(f'Wrote to {fp}')


def show_err_or_warn(e: Failed | Compiler.Warn, fp, file_content: str):
    if isinstance(e, Failed):
        color = '<red><b>'
        tag = f'<red><b>E{e.exception.code:02}'
        end_color = '</b></red>'
        ln = e.exception.line
        col = e.exception.col
        msg = e.exception.msg
        end_col = e.exception.end_col
        end_line = e.exception.end_line
        if isinstance(e.exception, CompilerError):
            filepath = e.exception.fp
            if e.compiler is None:
                ln = None
            else:
                file_content = e.compiler.sources[e.exception.fp]
        else:
            filepath = fp

    else:
        color = '<yellow><b>'
        end_color = '</b></yellow>'
        tag = '<yellow><b>Warning'
        col = e.col
        end_col = e.end_col
        end_line = e.end_line
        ln = e.line
        msg = e.message
        filepath = e.fp
        file_content = e.compiler.sources[e.fp]

    print()
    print(f'{tag}: {msg}:', file=sys.stderr)
    
    print(
        f'at {filepath}{f"<green>:{raw(str(ln + 1))}" if ln is not None else " <red>No line data available" + f":{str(col + 1)}" if col is not None else ""}',
        file=sys.stderr,
    )
    if ln is not None: # TODO: make the following more readable
        splitted = file_content.splitlines()
        if end_line is None or end_line == ln:
            from_lines = max(0, min(ln - 3, len(splitted)))
            to_lines = max(0, min(ln + 4, len(splitted)))
            for i, cln in enumerate(splitted[from_lines:to_lines], from_lines + 1):
                arr = f'{color}->{end_color}' if ln == i - 1 else '  '
                if ln == i-2 and col is not None:
                    print(f'<blue><d>          | </d></blue>{color}{' ' * col}{('^' * (end_col - col if end_col else 1))}') 
                print(f'{arr}<blue><d>{i:7} | </d></blue>{raw(cln)}', file=sys.stderr)
        elif end_col is not None:
            from_lines = max(0, min(ln - 3, len(splitted)))
            to_lines = max(0, min(end_line + 4, len(splitted)))
            for i, cln in enumerate(splitted[from_lines:to_lines], from_lines + 1):
                arr = f'{color}->{end_color}' if ln == i - 1 else '  '
                if ln == i-2 and col is not None:
                    print('<blue><d>       ... </d></blue>', file=sys.stderr)
                elif not ln < i-1 < end_line:
                    print(f'{arr}<blue><d>{i:7} | </d></blue>{raw(cln)}', file=sys.stderr)
                if ln <= i-1 <= end_line and col is not None:
                    if ln == i-1:
                        print(f'<blue><d>          | </d></blue>{color}{' ' * col}{('^' * (len(cln) - col))}', file=sys.stderr)
                    elif end_line == i-1:
                        print(f'<blue><d>          | </d></blue>{color}{('^' * end_col)}', file=sys.stderr)


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
            elif isinstance(e.value, Failed):  # `elif` for IDE type recognition
                if tracebacks:
                    raise e.value.exception
                show_err_or_warn(e.value, filepath, file_content)
                exit(1)  # Abort
            else:
                raise  # Impossible

    f = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.omc')
    try:
        f.write('\n'.join([str(x) for x in instructions]))
        # We need to close the file so that the subprocess can open it.
        f.close()
        vm_path = shutil.which('omvm')
        if (Path(__file__).parent / exec_name('omvm')).is_file():
            vm_path = Path(__file__).parent / exec_name('omvm')
        elif vm_path is None:
            print(
                '<red><b>Could not find `omvm` (OmniVM), which is required to run programs'
            )
            sys.exit(127)
        # run the VM and capture its output for tests, but also echo to user
        out = subprocess.run(
            [str(vm_path), 'run', f.name], capture_output=True
        )  # sourcery skip: python.lang.security.audit.dangerous-subprocess-use-audit
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
