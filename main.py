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
CLOSE_PAREN = "CLOSE_PAREN"
OPEN_PAREN = "OPEN_PAREN"
DOUBLE_QUOTE = 'DOUBLE_QUOTE"'
SINGLE_QUOTE = "SINGLE_QUOTE"
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
            self.current_idx+=2
            return Token(POW, None)
        elif current_char == "*":
            self.current_idx+=1
            return Token(MUL, None)
        elif current_char == "\n":
            self.current_idx+=1
            return Token(NEWLINE, None)
        elif current_char == "(":
            self.current_idx += 1
            return Token(OPEN_PAREN, None)
        elif current_char == ")":
            self.current_idx += 1
            return Token(CLOSE_PAREN, None)
        elif current_char == "/":
            self.current_idx += 1
            return Token(DIV, None)
        elif current_char == "'":
            self.current_idx+=1
            return Token(SINGLE_QUOTE, None)
        elif current_char == '"':
            self.current_idx += 1
            return Token(DOUBLE_QUOTE, None)
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
    def __init__(self, tokens:list[Token]):
        self.tokens = tokens
        self.current_token = self.tokens[0]
        self.pos = 0

    def eat(self, token_type):
        if self.current_token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type}, got {self.current_token.type}"
            )
        self.advance()
    
    def advance(self):
        self.pos +=1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(EOF, None)
    def expr(self):
        node = self.term()
        while self.current_token and self.current_token.type in (ADD, SUB):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.term())
        return node

    def term(self):
        node = self.power()
        while self.current_token and self.current_token.type in (MUL, DIV):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.power())
        return node

    def power(self):
        node = self.factor()
        if self.current_token and self.current_token.type == POW:
            op = self.current_token.type
            self.eat(POW)
            node = BinOp(node, op, self.power())  # right-associative
        return node

    def factor(self):
        token = self.current_token
        if token.type == INT:
            self.eat(INT)
            return Number(token.value)
        elif token.type == IDENTIFIER:
            self.eat(IDENTIFIER)
            return Variable(token.value)
        elif token.type == OPEN_PAREN:
            self.eat(OPEN_PAREN)
            node=self.expr()
            self.eat(CLOSE_PAREN)
            return node
        else:
            raise SyntaxError(f"Unexpected token {token.value}")

    def statement(self):
        if self.current_token.type == IDENTIFIER:
            next_tok = self.peek()
            if next_tok and next_tok.type == ASSIGN:
                name = self.current_token.value
                self.eat(IDENTIFIER)
                self.eat(ASSIGN)
                value = self.expr()
                return Assign(name, value)
        return self.expr()
    def peek(self):
        idx = self.pos+1
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(EOF, None)
            
def eval_ast(node, env:dict):
    if isinstance(node, Number):
        return node.value
    if isinstance(node, BinOp):
        left = eval_ast(node.left, env)
        right = eval_ast(node.right, env)

        if node.op == ADD:
            return left + right
        elif node.op == MUL:
            return left * right
        elif node.op == SUB:
            return left - right
        elif node.op == DIV:
            return left / right
        elif node.op == POW:
            return left ** right
    if isinstance(node, Variable):
        if node.name not in env.keys():
            raise NameError(f"Could not find a variable called {node.name}")
        return env[node.name]
    if isinstance(node, Assign):
        value = eval_ast(node.value, env)
        env[node.name] = value
        return value
    raise RuntimeError("Unknown node")

class ASTNode:
    pass

class Number(ASTNode):
    def __init__(self, value:int):
        self.value = value

    def __repr__(self) -> str:
        return f"Number({self.value})"
class BinOp(ASTNode):
    def __init__(self, left:ASTNode, op:str, right:ASTNode):
        self.op = op
        self.left = left
        self.right = right
    
    def __repr__(self) -> str:
        return f"BinOp({self.left}, {self.op}, {self.right})"

class Variable(ASTNode):
    def __init__(self, name:str):
        self.name = name
    def __repr__(self):
        return f"Variable({self.name})"
class Assign(ASTNode):
    def __init__(self, name:str, value:ASTNode):
        self.name = name
        self.value = value
    def __repr__(self):
        return f"Assign({self.name}, {self.value})"
def main():
    pass
if __name__ == "__main__":
    main()
