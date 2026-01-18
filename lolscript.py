from typer import Typer
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, Token, Program, Compiler
import base_env
import copy
import tempfile
import subprocess
app = Typer()

class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path

def comp(filepath:Path):
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
    instructions = compiler.compile(program)
    return instructions
@app.command()
def compile(filepath:Path):
    instructions = comp(filepath)
    with open("test.lsc", "w") as file:
        file.write("\n".join([str(x) for x in instructions]))

@app.command()
def run(filepath:Path, debug:bool = False):
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