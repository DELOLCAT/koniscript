import typer
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

def comp(filepath:Path, features = []):
    current_env = copy.copy(base_env.compiler_env)  # noqa: F841
    with open(filepath) as file:
        file_content = file.read()
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
    instructions = compiler.compile(program, features, file_content)
    return instructions

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
    with open("test.lsc", "w") as file:
        file.write("\n".join([str(x) for x in instructions]))
def compile_release(filepath: Path):
    instructions = comp(filepath)
    with open("test.lsc", "w") as file:
        file.write("\n".join([str(x) for x in instructions]))
 
@app.command()
def run(filepath:Path, debug:bool = False, features = []):
    ins = comp(filepath)
    with tempfile.NamedTemporaryFile(delete=True, mode="w+") as f:
        f.write("\n".join([str(x) for x in ins]))
        f.flush()
        subprocess.run(
            [
                "/home/ahmad/coding/rpn/vm",
                "run",
                f.name
            ]
        )
if __name__ == "__main__":
    app()