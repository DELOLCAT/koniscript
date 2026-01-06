from typer import Typer
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, Token
from base_env import env
import copy

app = Typer()

class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path
    
@app.command()
def interpret(filepath:Path):
    current_env = copy.copy(env)
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



if __name__ == "__main__":
    app()