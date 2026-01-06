from typer import Typer
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, BuiltinFunction, Token
import time

app = Typer()

class FileNotReadable(Exception):
    def __init__(self, path):
        self.path = path
    
@app.command()
def interpret(filepath:Path):
    env = {
        'print': BuiltinFunction('print', print),
        'sleep': BuiltinFunction('sleep', time.sleep),
        'input': BuiltinFunction('input', input)
    }
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
    #print(tkns)
    psr = Parser(tkns)
    program = psr.program()
    for ast in program.statements:
        eval_ast(ast, env)




if __name__ == "__main__":
    app()