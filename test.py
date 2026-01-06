from main import Tokenizer, Parser, EOF, eval_ast, BuiltinFunction, IncompleteInput
from rich import print
from rich.pretty import pprint
import time

env = {
    "print":BuiltinFunction('print', print),
    "sleep":BuiltinFunction('sleep', time.sleep)
}
while True:
    buffer = ""
    tknr = Tokenizer(input(">>> "))
    tkns = []

    while True:
        tkn = tknr.get_next_token()
        if tkn.type == EOF:
            break
        tkns.append(tkn)

    psr = Parser(tkns)
    try:
        ast = psr.statement()
    except IncompleteInput:
        
    #pprint(ast)
    try:
        print(eval_ast(ast, env))
    except Exception as e:
        print(f"[red b i u]Encountered error: {e}")
    #print(env)