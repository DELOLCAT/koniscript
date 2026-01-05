from typing import Any
from rich import print

ADD = "ADD"
INTEGER = "INT"
INT = INTEGER
IDENTIFIER = "IDENTIFIER"
ASSIGN = "ASSIGN"
NEWLINE = "NEWLINE"

class Token():
    def __init__(self, cat:str, value:Any):
        self.type = cat
        self.value = value
    def __str__(self):
        return f"Token({self.type}, {self.value})"
    def __repr__(self) -> str:
        return self.__str__()
    
class Tokenizer():
    def __init__(self, string: str):
        self.string:str = string
        self.current_idx:int = 0
        self.current_token:Token | None = self.get_next_token() 
    def get_current_char(self) -> str | None:
        if self.current_idx >= len(self.string):
            return None
        return self.string[self.current_idx]
    
    def skip_whitespace(self):
        while True:
            ch = self.get_current_char()
            if ch is not None and ch.isspace() and ch != "\n":
                self.current_idx += 1
            else:
                break

    def get_next_token(self):
        self.skip_whitespace()

        current_char = self.get_current_char()
        if current_char is None:
            return None  # End of input

        if current_char.isdigit():
            value = ""
            while self.get_current_char() is not None and self.get_current_char().isdigit():
                value += self.get_current_char() # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            return Token(INT, int(value))
        elif current_char == "+":
            self.current_idx+=1
            #self.current_token
            return Token(ADD, None)
        elif current_char == "=":
            self.current_idx+=1
            return Token(ASSIGN, None)
        elif current_char == "\n":
            self.current_idx+=1
            return Token(NEWLINE, None)
        elif current_char.isalpha():
            to_return = current_char
            self.current_idx+=1
            while self.get_current_char() is not None and self.get_current_char().isalnum(): # pyright: ignore[reportOptionalMemberAccess]
                to_return += self.get_current_char() # pyright: ignore[reportOperatorIssue]
                self.current_idx+=1
            return Token(IDENTIFIER, to_return)

        raise SyntaxError(f'Unexpected token "{current_char}"')
    
    def eat(self, expected_type:str):
        if self.current_token is None:
            raise SyntaxError('Unexpected end of input')
        if self.current_token.type != expected_type:
            raise SyntaxError(f'Expected {expected_type}, got {self.current_token.type} ({self.current_token.value})')
        self.current_token = self.get_next_token()
    def get_all_tokens(self) -> list[Token]:
        tkns=[]
        while self.current_token is not None:
            tkns.append(self.current_token)
            self.current_token = self.get_next_token()
        return tkns

def expr(tokens: list[Token | None]):
    stack = []
    for token in tokens:
        if token is None:
            raise SyntaxError('Unexpected end of input')     
        if token.type == INT:
            stack.append(token.value)
        elif token.type == ADD:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(rhs + lhs)
        else:
            raise SyntaxError(f'Unexpected token {token.type}. Expected INT or ADD')
    return stack[0]


def main():
    tknr = Tokenizer("hello=4 5+")
    tkns=tknr.get_all_tokens()
    i=0
    #print(tknr.current_token)
    #print(tknr.get_all_tokens())
    #print(expr(tknr.get_all_tokens()))
if __name__ == "__main__":
    main()
