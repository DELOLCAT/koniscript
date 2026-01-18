from typer import Typer
from rich import print  # noqa: F401
from rich.traceback import install
from pathlib import Path
import base_env
import main
from runtime import TYPES
from runtime import to_type
from typing import Self, Any, SupportsIndex
install()
app = Typer()
PUSH = "PUSH"
LOAD = "LOAD"
CALL = "CALL"


class Env():
    def __init__(self, parent:Self |None = None, values:list[tuple[int, Any] | None] = []):
        self.values: list[tuple[int, Any] | None]  = values
        self.parent = parent

class Frame():
    def __init__(self, ret_addr:int | None, env:Env, ln:int | None):
        self.env = env
        self.return_address = ret_addr
        self.stack = []
        self.ln = ln


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
    def __init__(self, content:list[str], global_env:list = base_env.VMenv, debug:bool=False):
        self.global_env = global_env
        main_frame = Frame(None, Env(), None)
        self.frames:list[Frame] = [main_frame]
        self.i = 0        
        self.const_pool=[]
        self.content=content
        self.builtin_count = len(global_env)
        self.dbg:bool = debug
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
        lines_start = -1
        for i,idx in enumerate(self.content):
            if idx.strip() == ".line":
                lines_start=i+1
                break
        if lines_start == -1:
            self.sup_lines = False
        else:
            self.sup_lines = True
            self.lines:list[int] = [int(x) for x in self.content[lines_start:]]
            self.content = self.content[:lines_start-1]
    def append_to_stack(self, item:tuple[int, Any]):
        self.frames[-1].stack.append(item)
    def pop_from_stack(self, i:SupportsIndex=-1):
        return self.frames[-1].stack.pop(i)
    def run(self):
        while self.i < len(self.content):
            try:
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
                        self.append_to_stack(self.const_pool[operands[0]])
                    case "RETRIEVE":  # noqa: F841
                        env = self.frames[-1].env
                        depth = operands[1]
                        idx = operands[0]
                        for _ in range(depth):
                            if env.parent is None:
                                raise RuntimeError("Depth is too high")
                            env = env.parent
                        val = env.values[idx]
                        if val is None:
                            raise RuntimeError(f"Could not find variable at {depth}:{idx}")
                        self.append_to_stack(val)
                    case "PUSH_BUILTIN":
                        self.append_to_stack(self.global_env[operands[0]])
                    case "CALL":
                        #to_call = stack.pop(0)
                        args = []
                        for _ in range(op):
                            args.append(self.pop_from_stack())
                        args.reverse()
                        to_call = self.pop_from_stack()
                        if to_call[0] != TYPES[main.FUNC]:
                            raise RuntimeError("Not a function")
                        to_call = to_call[1]
                        if to_call["type"] == "builtin":
                            self.append_to_stack((to_call["func"](*args)))
                        else:
                            local_count = to_call["local_count"]
                            param_count = to_call["params"]
                            env = Env(
                                to_call["closure"],
                                [None] * local_count
                            )
                            
                            
                            # Copy arguments into locals
                            for i in range(param_count):
                                env.values[i] = args[i]
                            if self.sup_lines:
                                frame = Frame(
                                    self.i,
                                    env,
                                    self.lines[self.i]
                                )
                            else:
                                frame = Frame(
                                    self.i,
                                    env,
                                    None
                                )

                            self.frames.append(frame)
                            self.i = to_call["entry"]
                            continue

                    case "STORE":
                        env = self.frames[-1].env
                        depth = operands[1]
                        slot = operands[0]
                        for _ in range(depth):
                            if env.parent is None:
                                raise RuntimeError("Frame has no parent")
                            env = env.parent
                        while len(env.values) <= slot:
                            env.values.append(None)
                        env.values[slot] = self.pop_from_stack()

                    case "JMPIF":
                        cond = self.pop_from_stack()
                        if cond[0] != TYPES[main.BOOL]:
                            raise RuntimeError(f"Invalid type: {cond[0]}")
                        if base_env.vm_to_bool(cond)[1]:
                            self.i = op + 1
                            continue
                    case "JMPIFF":
                        cond = self.pop_from_stack()
                        if cond[0] != TYPES[main.BOOL]:
                            raise RuntimeError(f"Invalid type: {cond[0]}")
                        if not base_env.vm_to_bool(cond)[1]:
                            self.i = op
                            continue
                    case "JMP":
                        self.i = op
                        continue
                    case "POP":
                        self.pop_from_stack()
                    case "MAKE_FUNCTION":
                        func = {
                            "type":"user",
                            "entry":operands[0],
                            "local_count":operands[1],
                            "params":operands[2],
                            "closure":self.frames[-1].env
                        }
                        self.append_to_stack((TYPES[main.FUNC], (func)))
                    case "RET":
                        if len(self.frames) <= 1:
                            raise RuntimeError("Cannot return while in main frame")
                        return_addr = self.frames[-1].return_address
                        if return_addr is None:
                            raise RuntimeError("Invalid return address")
                        to_ret = self.pop_from_stack()
                        self.i = return_addr
                        self.frames.pop()
                        self.append_to_stack(to_ret)
                    case _:
                        if ins in main.OPCODE_MAP:
                            rhs = self.pop_from_stack()
                            lhs = self.pop_from_stack()
                            key = (ins, int(lhs[0]), int(rhs[0]))
                            if key not in base_env.OP_TYPES:
                                raise RuntimeError("Invalid operand types")
                            lhs = to_type(lhs)
                            rhs = to_type(rhs)
                            ans = main.OPERATORS[main.OPCODE_MAP[ins]](lhs, rhs)
                            res_type = base_env.OP_TYPES[key]
                            self.append_to_stack((res_type,ans))
                        else:
                            raise NotImplementedError()
                self.i+=1
            except Exception as e:
                if self.sup_lines:
                    if self.dbg:
                        raise RuntimeError(f"{e}\n"
                                           f"at ins {self.i}\n"
                                           f"at source ln {self.lines[self.i] + 1}\n"
                                           f"Note: turn off debug to get a stack trace")
                    else:
                        print(f"[red b i u]{e}\n"
                              f"at instruction {self.i}\n"
                              f"at source ln {self.lines[self.i] + 1}\n[/]"
                               "[blue b]Traceback: (most recent call last)")
                        for frame in reversed(self.frames):
                            if frame.ln is None:
                                print("at [blue b]main stack[/]")
                                continue
                            print(f"ln [blue b]{frame.ln - 1}[/]")
                        return RuntimeError
                        
                else:
                    raise RuntimeError(f"{e}"
                                        "at ins {self.i}")


@app.command()
def run(filepath:Path):
    with open(filepath) as file:
        content = file.readlines()
    vm = VM(content)
    vm.run()
if __name__ == "__main__":
    app()