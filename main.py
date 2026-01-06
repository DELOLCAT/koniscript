from typing import Any
# from rich import print

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
RPAREN = "RPAREN"
LPAREN = "LPAREN"
STRING = "STRING"
COMMA = "COMMA"
PRECEDENCE = {ADD: 1, SUB: 1, MUL: 2, DIV: 2, POW: 3}

OPERATORS = {
    ADD: lambda a, b: a + b,
    SUB: lambda a, b: a - b,
    MUL: lambda a, b: a * b,
    DIV: lambda a, b: a / b,
    POW: lambda a, b: a**b,
}


class Callable:
    pass


class IncompleteInput(Exception):
    pass


class Token:
    def __init__(self, cat: str, value: Any):
        self.type = cat
        self.value = value

    def __str__(self):
        return f"Token({self.type}, {self.value})"

    def __repr__(self) -> str:
        return self.__str__()


class Tokenizer:
    def __init__(self, string: str):
        self.string: str = string
        self.current_idx: int = 0

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
            return self.string[self.current_idx + 1]
        else:
            return None

    def get_next_token(self):
        self.skip_whitespace()

        current_char = self.get_current_char()
        if current_char is None:
            return Token(EOF, None)  # End of input

        if current_char.isdigit():
            value = ""
            while (
                self.get_current_char() is not None
                and self.get_current_char().isdigit()  # pyright: ignore[reportOptionalMemberAccess]
            ):  # pyright: ignore[reportOptionalMemberAccess]
                value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            return Token(INT, int(value))
        elif current_char == "+":
            self.current_idx += 1
            # self.current_token
            return Token(ADD, None)
        elif current_char == "=":
            self.current_idx += 1
            return Token(ASSIGN, None)
        elif current_char == "-":
            self.current_idx += 1
            return Token(SUB, None)
        elif current_char == "*" and self.peek() == "*":
            self.current_idx += 2
            return Token(POW, None)
        elif current_char == "*":
            self.current_idx += 1
            return Token(MUL, None)
        elif current_char == "\n":
            self.current_idx += 1
            return Token(NEWLINE, None)
        elif current_char == "(":
            self.current_idx += 1
            return Token(LPAREN, None)
        elif current_char == ")":
            self.current_idx += 1
            return Token(RPAREN, None)
        elif current_char == "/":
            self.current_idx += 1
            return Token(DIV, None)
        elif current_char == ",":
            self.current_idx += 1
            return Token(COMMA, None)
        elif current_char == '"':
            self.current_idx += 1
            value = ""
            while (
                self.get_current_char() is not None and self.get_current_char() != '"'
            ):
                value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            if self.get_current_char() != '"':
                raise SyntaxError("Unterminated string literal")
            self.current_idx += 1
            return Token(STRING, value)

        elif current_char.isalpha():
            to_return = current_char
            self.current_idx += 1
            while (
                self.get_current_char() is not None
                and self.get_current_char().isalnum()  # pyright: ignore[reportOptionalMemberAccess]
            ):  # pyright: ignore[reportOptionalMemberAccess]
                to_return += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            return Token(IDENTIFIER, to_return)

        raise SyntaxError(f'Unexpected token "{current_char}"')


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0
        if self.tokens:
            self.current_token = self.tokens[0]
        else:
            self.current_token = Token(EOF, None)

    def eat(self, token_type):
        if self.current_token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {self.current_token.type}")
        self.advance()

    def advance(self):
        self.pos += 1
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
        elif token.type == STRING:
            self.eat(STRING)
            return String(token.value)
        elif token.type == IDENTIFIER:
            self.eat(IDENTIFIER)
            name = token.value
            if self.current_token.type == LPAREN:
                self.eat(LPAREN)
                args = []
                if self.current_token.type == EOF:
                    raise IncompleteInput
                if self.current_token.type != RPAREN:
                    args.append(self.expr())
                    while self.current_token.type == COMMA:
                        self.eat(COMMA)
                        args.append(self.expr())
                if self.current_token.type != RPAREN:
                    raise IncompleteInput
                self.eat(RPAREN)
                return Call(Variable(name), args)
            return Variable(token.value)

        elif token.type == LPAREN:
            self.eat(LPAREN)
            node = self.expr()
            if self.current_token.type == EOF:
                raise IncompleteInput
            self.eat(RPAREN)
            return node
        elif token.type == NEWLINE or token.type == EOF:
            raise SyntaxError(f"Unexpected token {token}")
        else:
            raise SyntaxError(f"Unexpected token {token}")

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
        idx = self.pos + 1
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(EOF, None)

    def parse(self):
        node = self.statement()
        if self.current_token.type != EOF:
            raise SyntaxError(
                f"Unexpected token of type {self.current_token.type}: {self.current_token.value}"
            )
        return node

    def program(self):
        statements = []
        while self.current_token.type != EOF:
            if self.current_token.type == NEWLINE:
                self.eat(NEWLINE)
                continue
            statements.append(self.statement())
        return Program(statements)


class ASTNode:
    pass


class Program(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self) -> str:
        return f"Program({self.statements})"


class Number(ASTNode):
    def __init__(self, value: int):
        self.value = value

    def __repr__(self) -> str:
        return f"Number({self.value})"


class Call(ASTNode):
    def __init__(self, func, args):
        self.func = func
        self.args = args

    def __repr__(self) -> str:
        return f"Call({self.func}, {self.args})"


class BinOp(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"BinOp({self.left}, {self.op}, {self.right})"


class Variable(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return f"Variable({self.name})"


class Assign(ASTNode):
    def __init__(self, name: str, value: ASTNode):
        self.name = name
        self.value = value

    def __repr__(self):
        return f"Assign({self.name}, {self.value})"


class BuiltinFunction(Call):
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __call__(self, args) -> Any:
        return self.func(*args)


class String(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"String({self.value})"


def eval_ast(node: ASTNode, env: dict):
    if isinstance(node, Number):
        return node.value
    if isinstance(node, BinOp):
        left = eval_ast(node.left, env)
        right = eval_ast(node.right, env)

        try:
            return OPERATORS[node.op](left, right)
        except TypeError:
            raise TypeError(f"Invalid operands for {node.op}")

    if isinstance(node, Call):
        fn = eval_ast(node.func, env)
        args = [eval_ast(arg, env) for arg in node.args]

        if isinstance(fn, BuiltinFunction):
            return fn(args)

        call_env = env.copy()
        for name, value in zip(fn.params, args):
            call_env[name] = value
        return eval_ast(fn.body, call_env)
    if isinstance(node, Variable):
        if node.name not in env.keys():
            raise NameError(f"Could not find a variable called {node.name}")
        return env[node.name]
    if isinstance(node, Assign):
        value = eval_ast(node.value, env)
        env[node.name] = value
        return value
    if isinstance(node, String):
        return node.value
    raise RuntimeError(f"Unknown node {node}")


def main():
    pass


if __name__ == "__main__":
    main()
