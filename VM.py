from typer import Typer
from rich import print  # noqa: F401
from rich.pretty import pprint  # noqa: F401
from pathlib import Path
import base_env 
import main

from runtime import TYPES

app = Typer()
PUSH = "PUSH"
LOAD = "LOAD"
CALL = "CALL"

class Frame():
    def __init__(self, args:list, return_addr:int | None, fp:int | None, env: list):
        self.args:list = args
        self.return_addr:int   | None = return_addr
        self.frame_pointer:int | None = fp
        self.lv = env.copy()  # Copy to avoid modifying the global env
        self.tmpstk:list = []
    def set_var(self, var, value):
        while len(self.lv) <= var:
            self.lv.append(None)
        self.lv[var] = value


def eval_str(string:str):
    i = 0
    output = ""
    if not string[0].isdigit():
        raise RuntimeError(f"Expected type annotation, got {string[0]}")
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
    return int(type_annot), output  # Convert type_annot to int
        
    
class VM():
    def __init__(self, content:list[str], global_env:list = base_env.VMenv):
        self.global_env = global_env
        self.stack = []
        main_frame = Frame([], None, None, global_env)
        self.frames:list[Frame] = [main_frame]
        self.i = 0
        self.frames[-1].tmpstk.append
        self.const_pool=[]
        self.content=content
        self.builtin_count = len(global_env)
        while True:
            if content[self.i].strip() == "" or content[self.i].strip() == ".const":
                self.i+=1
                continue
            if content[self.i].strip() == ".code":
                self.i+=1
                break
            self.const_pool.append(eval_str(self.content[self.i]))
            self.i+=1
        self.content = self.content[self.i:]
        self.i:int =0

    def set_var(self, var, value):
        self.frames[-1].set_var(var, value)
    def run(self):
        while self.i < len(self.content):
            while self.content[self.i].strip() == "":
                self.i+=1
            buf = self.content[self.i].strip().split()
            ins = buf[0]
            if len(buf) > 1:
                op = int(buf[1])
            operands = [int(x) for x in buf[1:]]
            match ins:
                case "NOP":
                    pass
                case "PUSH_CONST":  # noqa: F841
                    self.frames[-1].tmpstk.append(self.const_pool[op])
                case "RETRIEVE":  # noqa: F841
                    self.frames[-1].tmpstk.append(self.frames[-1].lv[op])
                case "CALL":
                    #to_call = stack.pop(0)
                    args = []
                    for _ in range(op):
                        args.append(self.frames[-1].tmpstk.pop())
                    args.reverse()
                    to_call = self.frames[-1].tmpstk.pop()
                    if to_call[0] != TYPES[main.FUNC]:
                        raise RuntimeError("Not a function")
                    to_call = to_call[1]
                    if to_call["type"] == "builtin":
                        self.frames[-1].tmpstk.append((to_call["func"](*args)))
                    else:
                        local_count = to_call["local_count"]
                        param_count = to_call["params"]

                        frame = Frame(
                            args,
                            self.i,
                            None,
                            self.frames[-1].lv
                        )

                        # Allocate locals
                        frame.lv += [None] * param_count
                        base = self.builtin_count
                        # Copy arguments into locals
                        for i in range(param_count):
                            frame.lv[base + i] = args[i]

                        self.frames.append(frame)
                        self.i = to_call["entry"]
                        continue

                case "STORE":
                    self.set_var(op, self.frames[-1].tmpstk.pop())
                case "JMPIF":
                    cond = self.frames[-1].tmpstk.pop()
                    if cond[0] != TYPES[main.BOOL]:
                        raise RuntimeError(f"Invalid type: {cond[0]}")
                    if cond[1]:
                        self.i = op + 1
                        continue
                case "JMPIFF":
                    cond = self.frames[-1].tmpstk.pop()
                    if cond[0] != TYPES[main.BOOL]:
                        raise RuntimeError(f"Invalid type: {cond[0]}")
                    if not cond[1]:
                        self.i = op
                        continue
                case "JMP":
                    self.i = op
                    continue
                case "POP":
                    self.frames[-1].tmpstk.pop()
                case "MAKE_FUNCTION":
                    func = {
                        "type":"user",
                        "entry":operands[0],
                        "local_count":operands[1],
                        "params":operands[2]
                    }
                    self.frames[-1].tmpstk.append((TYPES[main.FUNC], (func)))
                case "RET":
                    if len(self.frames) <= 1:
                        raise RuntimeError("Cannot return while in main frame")
                    return_addr = self.frames[-1].return_addr
                    if return_addr is None:
                        raise RuntimeError("Invalid return address")
                    to_ret = self.frames[-1].tmpstk.pop()
                    self.i = return_addr
                    self.frames.pop()
                    self.frames[-1].tmpstk.append(to_ret)
                case _:
                    if ins in main.OPCODE_MAP:
                        rhs = self.frames[-1].tmpstk.pop()
                        lhs = self.frames[-1].tmpstk.pop()
                        key = (ins, int(lhs[0]), int(rhs[0]))
                        if key not in base_env.OP_TYPES:
                            raise RuntimeError("Invalid operand types")
                        ans = main.OPERATORS[main.OPCODE_MAP[ins]](lhs[1], rhs[1])
                        res_type = base_env.OP_TYPES[key]
                        self.frames[-1].tmpstk.append((res_type,ans))
                    else:
                        raise NotImplementedError()
            self.i+=1


@app.command()
def run(filepath:Path):
    with open(filepath) as file:
        content = file.readlines()
    vm = VM(content)
    vm.run()
@app.command()
def test():
    print(eval_str(input(">>> ")))
if __name__ == "__main__":
    app()
