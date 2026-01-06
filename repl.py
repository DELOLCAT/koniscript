from main import Tokenizer, Parser, EOF, eval_ast, IncompleteInput
from rich import print
import copy
from base_env import env
buffer = ""

while True:
    current_env = copy.copy(env)
    line = input(">>> " if not buffer else "... ")
    buffer += line
    try:
        tknr = Tokenizer(buffer)
        tkns = []
        while True:
            tkn = tknr.get_next_token()
            if tkn.type == EOF:
                tkns.append(tkn)
                break
            tkns.append(tkn)
        psr = Parser(tkns)
        ast = psr.statement()
        print(eval_ast(ast, env))
        buffer = ""
    except IncompleteInput:
        continue
    except SyntaxError as e:
        print(f"[red i b u]Syntax Error: {e}")
