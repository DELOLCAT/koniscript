from typer import Typer
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, Token, Program, Compiler
import base_env
import copy

app = Typer()

class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path
    
@app.command()
def interpret(filepath:Path):
    current_env = copy.copy(base_env.env)
    with open(filepath) as file:
        if not file.readable():
            raise FileNotReadable(filepath)
        file_content = file.read()
    tknr = Tokenizer(file_content)
    tkns:list[Token] = []
    while True:
        tkn = tknr.get_next_token()
        tkns.append(tkn)
        if tkn.type == EOF:
            break
    psr = Parser(tkns)
    program = psr.program()
    pos = 1
    try:
        for ast in program.statements:
            eval_ast(ast, current_env)
            pos+=1
    except Exception as e:
        print(f"[red i b u]{e} on line {pos}")
        raise



@app.command()
def compile(filepath:Path):
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
    psr:Parser = Parser(tkns)
    program:Program = psr.program()
    compiler =  Compiler(current_env, base_env.ASTenv)
    instructions = compiler.compile(program)
    with open("test.lsc", "w") as file:
        file.write("\n".join(instructions))

    

if __name__ == "__main__":
    app()