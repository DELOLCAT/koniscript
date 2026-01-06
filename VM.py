from typer import Typer
from rich import print  # noqa: F401
from rich.pretty import pprint  # noqa: F401
from pathlib import Path
import base_env 
import main
from enum import Enum


app = Typer()
PUSH = "PUSH"
LOAD = "LOAD"
CALL = "CALL"

def eval_str(string:str):
    i = 1
    output = ""
    if string[0] != '"':
        raise RuntimeError(f"Expected string, got {string[0]}")
    term = False
    while i < len(string):
        if string[i] == '"':
            term = True
            break
        if string[i] == "\\":
            i+=1
            if string[i] == "n":
                output+="\n"
            else:
                output+=string[i]
            i+=1
            continue
        output += string[i]
        i+=1
    if not term:
        raise RuntimeError("Unterminated string literal in VM code")
    return output
        
def set_var(var, value, vars):
    if len(vars)+1 > var:
        vars.append(None)
    vars[var] = value

@app.command()
def run(filepath: Path):
    with open(filepath) as file:
        content = file.readlines()
    #env = base_env.env
    stack = []
    i=0
    ###.const
    const_pool = []
    while True:
        if content[i].strip() == "" or content[i].strip() == ".const":
            i+=1
            continue
        if content[i].strip() == ".code":
            i+=1
            break
        const_pool.append(eval_str(content[i]))
        i+=1

    
    vars = list(base_env.env.values.values())
    ###.code
    while i < len(content):
        while content[i].strip() == "":
            i+=1
        
        ins = content[i].split()[0]
        if len(content[i].strip().split()) > 1:
            v = int(" ".join(content[i].strip().split()[1:]))
        match ins:
            case "PUSH_CONST":  # noqa: F841
                stack.append(const_pool[v])
            case "RETRIEVE": # noqa: F841
                stack.append(vars[v])
            case "CALL":
                #to_call = stack.pop(0)
                args = []
                for _ in range(v):
                    args.append(stack.pop())
                args.reverse()
                to_call = stack.pop()
                if isinstance(to_call, main.BuiltinFunction):
                    stack.append(to_call.func(*args))
                else:
                    raise NotImplementedError()
            case "STORE":
                set_var(v, stack[len(stack)-1], vars)
            case _:
                if ins in main.OPCODE_MAP:
                    rhs = stack.pop()
                    lhs = stack.pop()
                    stack.append(main.OPERATORS[main.OPCODE_MAP[ins]](lhs, rhs))
                else:
                    raise NotImplementedError()
        i+=1
            
            
@app.command()
def test():
    print(eval_str(input(">>> ")))
if __name__ == "__main__":
    app()
