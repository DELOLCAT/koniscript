from main import Tokenizer, Parser, EOF, eval_ast, BuiltinFunction, IncompleteInput
from rich.prompt import Prompt
from rich import print
import time
buffer = ""
env = {
    "print":BuiltinFunction('print', print),
    "sleep":BuiltinFunction('sleep', time.sleep)
}
while True:
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
