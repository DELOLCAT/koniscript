import typer
import os
import sys
from pathlib import Path
from ray.main import Tokenizer, Parser, EOF, Token, Program, Compiler
from ray import base_env
import copy
import tempfile
import subprocess
import sys
from questionary import checkbox, Choice
app = typer.Typer()

def bundled_exe(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if sys.platform == "win32":
        name += ".exe"
    return base / name

    
class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path

def comp(filepath:Path, features=None):
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
    psr:Parser = Parser(tkns, base_env.ASTenv)
    program:Program = psr.program()
    compiler =  Compiler(current_env, base_env.ASTenv)
    return compiler.compile(program, features, file_content)

@app.command()
def compile(filepath:Path, 
            mode:bool = typer.Option(
                True,
                "--release/--debug"
            )):
    if mode:
        features = checkbox("What additional debug features do you want to include?", 
                                        [
                                            Choice("line info", "lines", description="Used in compiler errors to show line info."), 
                                            Choice("copy of source", value = "source", description="Used in compiler errors to show surrounding code, but only if `lines` is ticked, else it can be used for misc features."),
                                        ]).ask()
    else:
        features = []
    instructions = comp(filepath, features)
    with open(f"{str(filepath).removesuffix('.ray')}.rvm", "w") as file:
        file.write("\n".join([str(x) for x in instructions]))
 
@app.command()
def run(filepath:Path, debug:bool = False, features = []):
    # sourcery skip: default-mutable-arg
    ins = comp(filepath)
    f = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".rvm")
    try:
        f.write("\n".join([str(x) for x in ins]))
        # We need to close the file so that the subprocess can open it.
        f.close()
        
        subprocess.run(
            [
                bundled_exe("vm"),
                "run",
                f.name
            ]
        )
    finally:
        os.unlink(f.name)
if __name__ == "__main__":
    app()