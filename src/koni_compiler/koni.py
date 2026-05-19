from dataclasses import dataclass
import shutil
from typing import Generator
import typer
import os
import sys
from pathlib import Path
from colorama import init
from koni_compiler.main import (
    Tokenizer,
    Parser,
    TokenType,
    Token,
    Program,
    Compiler,
    CompilationException,
    Warn
)
from koni_compiler import base_env
import copy
import tempfile
import subprocess
from ansimarkup import ansiprint as print
from ansimarkup import raw
from time import perf_counter
init(True)
app = typer.Typer()


tracebacks = os.environ.get('KONI_TRACEBACKS')


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
    exception: CompilationException


@dataclass
class Success(CompilationResult):
    instructions: list[str]


def get_program(file_content: str, fp: str):
    try:
        SOURCES[str(fp)] = file_content
        current_env = copy.copy(base_env.compiler_env)
        tknr = Tokenizer(file_content, fp)
        tkns: list[Token] = []
        while True:
            tkn = tknr.get_next_token()
            if isinstance(tkn, list):
                tkns += tkn
            else:
                tkns.append(tkn)
            if tkns[-1].type == TokenType.EOF:
                break
        psr: Parser = Parser(tkns, base_env.ASTenv, fp=fp, file_content=file_content)
        program: Program = yield from psr.program()
        return program, current_env
    except CompilationException as e:
        return Failed(e)


def comp(
    file_content: str, filepath, features=None
) -> Generator[Warn | Compiler.ModuleRequest, Program, CompilationResult]:

    if features is None:
        features = []

    tmp = yield from get_program(file_content, filepath)

    if isinstance(tmp, Failed):
        return tmp

    program, current_env = tmp

    compiler = Compiler(current_env, base_env.ASTenv, base_env.attrs, str(filepath))

    try:
        cmp = compiler.compile(program, features, file_content)
    except CompilationException as e:
        return Failed(e)
    result = None
    while True:
        try:
            a = cmp.send(result)
            if isinstance(a, Compiler.ModuleRequest):
                if (Path(filepath).parent / (f'{a.name}.kn')).is_file():
                    fp = Path(filepath).parent / (f'{a.name}.kn')
                elif (Path(filepath).parent / 'packages' / (f'{a.name}.kn')).is_file():
                    fp = Path(filepath).parent / 'packages' / (f'{a.name}.kn')
                else:
                    raise CompilationException(
                        6,
                        f'Could not resolve module `{a.name}`',
                        a.line,
                        a.col,
                        a.end_line,
                        a.end_col,
                        compiler.mod_stack[-1].fp,
                    )  # TODO: columns

                content = fp.read_text()
                SOURCES[str(fp)] = content
                tmp = yield from get_program(content, fp)
                if isinstance(tmp, Failed):
                    return tmp
                import_program, _ = tmp
                result = Compiler.ModuleReceived(import_program, str(fp), content)

            else:
                result = None
                yield a
        except StopIteration as e:
            return Success(e.value)
        except CompilationException as e:
            return Failed(e)
SOURCES: dict[str, str] = {
    
}

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
        f'Compiling with <b><green>{out}</green></b>{" <d>(source+line info)</d>" if out == "debug" else ""}. <blue>See `koni compile --help` for more info</blue>'
    )
    file_content = Path(filepath).read_text()
    start_time = perf_counter()
    it = iter(comp(file_content, filepath, comp_features))

    instructions = None
    warns = 0
    while True:
        try:
            value = next(it)
            match value:
                case Warn():
                    warns += 1
                    show_err_or_warn(value)
        except StopIteration as e:
            if isinstance(e.value, Success):
                instructions = e.value.instructions
                break
            elif isinstance(e.value, Failed):
                if tracebacks:  # To show Python tracebacks for development
                    raise e.value.exception
                show_err_or_warn(e.value)
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
    fp = f'{str(filepath).removesuffix(".kn")}.knc'
    if warns > 0:
        print(
            f'<green>Compiled in <b>{round(perf_counter() - start_time, 3)}</b> seconds, </green><yellow><b>{warns} warnings emitted</b></yellow>'
        )
    else:
        print(f'<green>Compiled in <b>{round(perf_counter() - start_time, 3)}</b> seconds</green>')
    with open(fp, 'w') as file:
        file.write('\n'.join([str(x) for x in instructions]))
    print(f'Wrote to {fp}')


def show_err_or_warn(e: Failed | Warn):
    def eprint(*args: str):
        print(*args, file=sys.stderr)
    if isinstance(e, Failed):
        color = '<red><b>'
        tag = f'<red><b>E{e.exception.code:02}'
        end_color = '</b></red>'
        cls = e.exception

    else:
        color = '<yellow><b>'
        end_color = '</b></yellow>'
        tag = '<yellow><b>Warning'
        cls = e
    col = cls.col
    end_col = cls.end_col
    end_line = cls.end_line
    ln = cls.line
    msg = cls.message
    filepath = cls.fp

    file_content = SOURCES[str(filepath)]
    if end_line == ln:
        end_line = None
    
    RADIUS = 5

    eprint()
    eprint(f'{tag}: {msg}:')
    
    lns = file_content.splitlines()
    eprint(
        f'at {filepath}{f"<green>:{raw(str(ln + 1))}" if ln is not None else " <red>No line data available" + f":{str(col + 1)}" if col is not None else ""}',
    )
    def get_info_nl():
        start = max(ln - RADIUS, 0)
        end = min(ln + RADIUS, len(file_content.splitlines()))
        c = enumerate(lns[start:end+1], start+1)
        return c
    if end_line is None and end_col is None:
        c = get_info_nl()
        for n, lnc in c:
            if n == ln+1:
                eprint(f'{color}-><blue><b>{n: 5} |</b></blue>{end_color} {lnc}')
                eprint(f'<blue><b>        |</b></blue>{color}{(col+1) * ' '}^')
            else:
                eprint(f'<blue><b>{n: 7} |</b></blue> {lnc}')
    elif end_line is None and end_col is not None:
        c = get_info_nl()
        dist = end_col - col
        for n, lnc in c:
            if n == ln+1:
                eprint(f'{color}-><blue><b>{n: 5} |</b></blue>{end_color} {lnc}')
                eprint(f'<blue><b>        |</b></blue>{color}{(col+1) * ' '}{'^' * dist}')
            else:
                eprint(f'<blue><b>{n: 7} |</b></blue> {lnc}')
    elif end_line is not None and end_col is not None: # these conditions are big so Pyright knows the types
        start = max(ln - RADIUS, 0)
        end = min(end_line + RADIUS, len(file_content.splitlines()))
        c = enumerate(lns[start:end+1], start+1)
        for n, lnc in c:
            if n == ln+1:
                dist = len(lnc) - col
                eprint(f'{color}-><blue><b>{n: 5} |</b></blue>{end_color} {lnc}')
                eprint(f'<blue><b>        |</b></blue>{color} {(col) * ' '}{'^' * dist} from here')
            elif n == end_line+1:
                eprint(f'{color}<blue><b>{n: 7} |</b></blue>{end_color} {lnc}')
                eprint(f'<blue><b>        |</b></blue>{color} {'^' * end_col} to here')
            else:
                eprint(f'<blue><b>{n: 7} |</b></blue> {lnc}')
    for help in cls.helps:
        eprint(f'    <b><blue>help: </blue>{help.value}')
            

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
            if isinstance(value, Warn):
                show_err_or_warn(value)
        except StopIteration as e:
            if isinstance(e.value, Success):
                instructions = e.value.instructions
                break
            elif isinstance(e.value, Failed):  # `elif` for IDE type recognition
                if tracebacks:
                    raise e.value.exception
                show_err_or_warn(e.value)
                exit(1)  # Abort
            else:
                raise  # Impossible

    f = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.knc')
    try:
        f.write('\n'.join([str(x) for x in instructions]))
        # We need to close the file so that the subprocess can open it.
        f.close()
        vm_path = shutil.which('kovm')
        if (Path(__file__).parent / exec_name('kovm')).is_file():
            vm_path = Path(__file__).parent / exec_name('kovm')
        elif vm_path is None:
            print(
                '<red><b>Could not find `kovm` (koniscript VM), which is required to run programs', file=sys.stderr
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
