"""
This whole file is deprecated.
A new REPL is going to be developed in the future
"""


from main import Tokenizer, Parser, EOF, eval_ast, IncompleteInput
from rich import print
from rich.traceback import install
import copy
from base_env import env
buffer = ""

install()

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
        if ast is not None:
            print(eval_ast(ast, env))
        buffer = ""
    except IncompleteInput:
        continue