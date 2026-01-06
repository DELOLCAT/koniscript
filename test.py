from main import Tokenizer, Parser, EOF, eval_ast
from rich import print
from rich.pretty import pprint

env = {}
while True:
    tknr = Tokenizer(input("Gimme some input\n>>> "))
    tkns = []

    while True:
        tkn = tknr.get_next_token()
        if tkn.type == EOF:
            break
        tkns.append(tkn)

    psr = Parser(tkns)
    ast = psr.statement()
    #pprint(ast)
    print(eval_ast(ast, env))
    print(env)