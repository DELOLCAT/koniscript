from typing import Any
from rich import print

ADD = "ADD"
INTEGER = "INT"
INT = INTEGER
IDENTIFIER = "IDENTIFIER"
ASSIGN = "ASSIGN"
NEWLINE = "NEWLINE"
EOF = "EOF"
DIVIDE = "DIVIDE"
DIV = DIVIDE
MULTIPLY = "MULTIPLY"
MUL = MULTIPLY
POWER = "POWER"
POW = POWER
SUBTRACT = "SUBTRACT"
SUB = SUBTRACT

PRECEDENCE = {
    ADD:1,
    SUB:1,
    MUL:2,
    DIV:2,
    POW:3
}


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
    def peek(self):
        if self.current_idx + 1 < len(self.string):
            return self.string[self.current_idx+1]
        else:
            return None
    def get_next_token(self):
        self.skip_whitespace()

        current_char = self.get_current_char()
        if current_char is None:
            return Token(EOF, None)  # End of input

        if current_char.isdigit():
            value = ""
            while self.get_current_char() is not None and self.get_current_char().isdigit(): #pyright: ignore[reportOptionalMemberAccess]
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
        elif current_char == "-":
            self.current_idx+=1
            return Token(SUB, None)
        elif current_char == "*" and self.peek()=="*":
            self.current_idx+=1
            return Token(POW, None)
        elif current_char == "*":
            self.current_idx+=1
            return Token(MUL, None)
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
    
def infix_to_rpn(tokens: list[Token]) -> list[Token]:
    output: list[Token] = []
    operators: list[Token] = []

    for token in tokens:
        if token.type == INT or token.type == IDENTIFIER:
            output.append(token)

        elif token.type == ADD:
            while (
                operators
                and operators[-1].type == ADD
                and PRECEDENCE[operators[-1].type] >= PRECEDENCE[token.type]
            ):
                output.append(operators.pop())
            operators.append(token)

        else:
            raise SyntaxError(f"Unsupported token {token.type}")

    while operators:
        output.append(operators.pop())

    return output

def eval_rpm(tokens: list[Token | None]):
    stack = []
    for token in tokens:
        if token is None:
            raise SyntaxError('Unexpected end of input')     
        if token.type == INT:
            stack.append(token.value)
        elif token.type == ADD:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs + rhs)
        elif token.type == SUB:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs - rhs)
        elif token.type == MUL:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs * rhs)
        elif token.type == DIV:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs / rhs)
        else:
            raise SyntaxError(f'Unexpected token {token.type}. Expected INT or ADD')
    return stack[0]

class Parser:
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer
        self.current_token = self.tokenizer.get_next_token()

    def eat(self, expected_type: str):
        if self.current_token.type != expected_type:
            raise SyntaxError(
                f"Expected {expected_type}, got {self.current_token.type}"
            )
        self.current_token = self.tokenizer.get_next_token()





def main():
    pass
if __name__ == "__main__":
    main()
