from typer import Typer
from rich import print  # noqa: F401
from rich.pretty import pprint  # noqa: F401
from pathlib import Path
import base_env 
import main
from enum import Enum
from main import TYPES

app = Typer()
PUSH = "PUSH"
LOAD = "LOAD"
CALL = "CALL"

def eval_str(string:str):
    i = 0
    output = ""
    if not string[0].isdigit():
        RuntimeError(f"Expected type annotation, got {string[0]}")
    type_annot = ""
    term = False
    while i < len(string):
        if string[i] == '"':
            term=True
            i+=1
            break
        type_annot += string[i]
        i+=1
    if not term:
        raise RuntimeError("String never started")
    
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
    return type_annot, output
        
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

    content = content[i:]
    i=0
    vars = base_env.VMenv
    ###.code
    while i < len(content):
        while content[i].strip() == "":
            i+=1
        
        ins = content[i].split()[0]
        if len(content[i].strip().split()) > 1:
            op = int(" ".join(content[i].strip().split()[1:]))
        match ins:
            case "NOP":
                pass
            case "PUSH_CONST":  # noqa: F841
                stack.append(const_pool[op])
            case "RETRIEVE": # noqa: F841
                stack.append(vars[op])
            case "CALL":
                #to_call = stack.pop(0)
                args = []
                for _ in range(op):
                    args.append(stack.pop())
                args.reverse()
                to_call = stack.pop()
                if to_call[0] != TYPES[main.FUNC]:
                    raise RuntimeError("Not a function")
                to_call = to_call[1]
                if to_call["type"] == "builtin":
                    stack.append((to_call["func"](*args)))
                else:
                    raise NotImplementedError()
            case "STORE":
                set_var(op, stack.pop(), vars)
            case "JMPIF":
                cond = stack.pop()
                if cond[0] != TYPES[main.BOOL]:
                    raise RuntimeError(f"Invalid type: {cond[0]}")
                if cond[1]:
                    i = op + 1
                    continue
            case "JMPIFF":
                cond = stack.pop()
                if cond[0] != TYPES[main.BOOL]:
                    raise RuntimeError(f"Invalid type: {cond[0]}")
                if not cond[1]:
                    i = op
                    continue
            case "JMP":
                i = op
                continue
            case _:
                if ins in main.OPCODE_MAP:
                    rhs = stack.pop()
                    lhs = stack.pop()
                    key = (ins, int(lhs[0]), int(rhs[0]))
                    if key not in base_env.OP_TYPES:
                        raise RuntimeError("Invalid operand types")
                    ans = main.OPERATORS[main.OPCODE_MAP[ins]](lhs[1], rhs[1])
                    res_type = base_env.OP_TYPES[key]
                    stack.append((res_type,ans))
                else:
                    raise NotImplementedError()
        i+=1
            
            
@app.command()
def test():
    print(eval_str(input(">>> ")))
if __name__ == "__main__":
    app()
