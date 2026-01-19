import typer
import os
import sys
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, Token, Program, Compiler
import base_env
import copy
import tempfile
import subprocess
from questionary import checkbox, Choice
app = typer.Typer()

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

        if getattr(sys, 'frozen', False):
            # If the application is run as a bundle, the vm is in the same directory
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent

        vm_path = os.path.join(base_path, "vm")

        subprocess.run(
            [
                vm_path,
                "run",
                f.name
            ]
        )
    finally:
        os.unlink(f.name)
if __name__ == "__main__":
    app()