from typer import Typer
from pathlib import Path
from main import Tokenizer, Parser, EOF, eval_ast, Token, Program, Compiler
import base_env
import copy
from VM import VM
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
    psr:Parser = Parser(tkns)
    program:Program = psr.program()
    compiler =  Compiler(current_env, base_env.ASTenv)
    instructions = compiler.compile(program)
    return instructions
@app.command()
def compile(filepath:Path):
    instructions = comp(filepath)
    with open("test.lsc", "w") as file:
        file.write("\n".join(instructions))

@app.command()
def run(filepath:Path, write_to_file:bool=False, debug:bool = False):
    ins = comp(filepath)
    if write_to_file:
        with open("test.lsc", "w") as file:
            file.write("\n".join(ins))
    vm = VM(ins)
    vm.run()
    print("Exited. Debug info:")
    stack_len = 0
    for env in vm.frames:
        stack_len += len(env.stack)
    print(f"    Stack length: {stack_len}")

if __name__ == "__main__":
    app()