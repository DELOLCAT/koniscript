from typing import Any
import base_env
# from rich import print
from runtime import BuiltinFunction, TYPES, Environment, Module, ASTNode, Program, BuiltinModule, BuiltinModulePointer
from warnings import warn
import os
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
LBRACE = "LBRACE"
RBRACE = "RBRACE"
FUNC = "FUNC"
RETURN = "RETURN"
BOOLEAN = "BOOLEAN"
BOOL = BOOLEAN
GREATER_THAN = "GREATER_THAN"
GT = GREATER_THAN
LESS_THAN = "LESS_THAN"
LT = LESS_THAN
LTE = "LESS_THAN_OR_EQ"
GTE = "LESS_THAN_OR_EQ"
EQUAL_TO = "EQUAL_TO"
NOT_EQUAL_TO = "NOT_EQUAL_TO"
IF = "IF"
ELSE = "ELSE"
OR = "OR"
AND = "AND"
FLOAT = "FLOAT"
WHILE = "WHILE"
DOT = "DOT"
IMPORT = "IMPORT"
EXPORT = "EXPORT"
LBRACKET = "LBRACKET"
RBRACKET = "RBRACKET"
VALUES = [
    INT,
    STRING,
    IDENTIFIER      
]

OPERATORS = {
    ADD: lambda a, b: a + b,
    SUB: lambda a, b: a - b,
    MUL: lambda a, b: a * b,
    DIV: lambda a, b: a / b,
    POW: lambda a, b: a ** b,
    LT: lambda a, b: a < b,
    GT: lambda a, b: a > b,
    GTE: lambda a,b: a >= b,
    LTE: lambda a,b: a <= b,
    EQUAL_TO: lambda a, b: a == b,
    NOT_EQUAL_TO: lambda a, b: a != b,
    OR: lambda a, b: a or b,
    AND: lambda a, b: a and b
}

KEYWORDS = {
    "func": FUNC,
    "return":RETURN,
    "if":IF,
    "else":ELSE,
    "or":OR,
    "and":AND,
    "while": WHILE,
    "import": IMPORT,
    "export": EXPORT
}



class Callable:
    pass


class IncompleteInput(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value




class Token:
    def __init__(self, cat: str, value: Any, line:int, col:int):
        self.type = cat
        self.value = value
        self.line = line

    def __str__(self):
        return f"Token({self.type}, {self.value})"

    def __repr__(self) -> str:
        return self.__str__()


class Tokenizer:
    def __init__(self, string: str):
        self.string: str = string
        self.current_idx: int = 0
        self.line:int = 0
        self.col:int = 0
    def advance(self, steps:int = 1) -> str | None:
        for _ in range(steps):
            ch = self.get_current_char()
            if ch is None:
                return None
            self.current_idx+=1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return ch
    def get_current_char(self) -> str | None:
        if self.current_idx >= len(self.string):
            return None
        return self.string[self.current_idx]

    def skip_whitespace(self):
        while True:
            ch = self.get_current_char()
            if ch is not None and ch.isspace() and ch != "\n":
                self.advance()
            else:
                break

    def peek(self):
        if self.current_idx + 1 < len(self.string):
            return self.string[self.current_idx + 1]
        else:
            return None
    def check(self, text: str) -> bool:
        end = self.current_idx + len(text)
        return self.string[self.current_idx:end] == text
    def get_next_token(self):
        self.skip_whitespace()
        start_line = self.line
        start_col = self.col
        current_char = self.get_current_char()
        if current_char is None:
            return Token(EOF, None, start_line, start_col)  # End of input

        if current_char.isdigit():
            value = ""
            fl = False
            while (
                self.get_current_char() is not None
                and self.get_current_char().isdigit() # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char() == "."  # pyright: ignore[reportOptionalMemberAccess]
            ):
                if self.get_current_char() == ".":
                    fl = True
                value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.advance(1)
            if fl:
                return Token(FLOAT, float(value), start_line, start_col)
            else:
                return Token(INT, int(value), start_line, start_col)
        elif current_char == "[":
            self.advance(1)
            return Token(LBRACKET, None, start_line, start_col)
        elif current_char == "]":
            self.advance(1)
            return Token(RBRACKET, None, start_line, start_col)
    
        elif current_char == "#":
            while not self.get_current_char() == "\n":
                self.advance()
            return self.get_next_token()
        elif current_char == "+":
            self.advance(1)
            return Token(ADD, None, start_line, start_col)
        elif current_char == ".":
            self.advance(1)
            return Token(DOT, None, start_line, start_col)
        elif self.check("true"):
            self.advance(4)
            return Token(BOOL, True, start_line, start_col)
        elif self.check("false"):
            self.advance(5)
            return Token(BOOL, False, start_line, start_col)
        elif self.check("=="):
            self.advance(2)
            return Token(EQUAL_TO, None, start_line, start_col)
        elif current_char == "=":
            self.advance(1)
            return Token(ASSIGN, None, start_line, start_col)
        elif current_char == "-":
            self.advance(1)
            return Token(SUB, None, start_line, start_col)
        elif self.check("**"):
            self.advance(2)
            return Token(POW, None, start_line, start_col)
        elif current_char == "*":
            self.advance(1)
            return Token(MUL, None, start_line, start_col)
        elif self.check ("!="):
            self.advance(2)
            return Token(NOT_EQUAL_TO, None, start_line, start_col)
        elif self.check("<="):
            self.advance(2)
            return Token(LTE, None, start_line, start_col)
        elif self.check(">="):
            self.advance(2)
            return Token(GTE, None, start_line, start_col)
        elif current_char == "\n":
            self.advance(1)
            return Token(NEWLINE, None, start_line, start_col)
        elif current_char == "(":
            self.advance(1)
            return Token(LPAREN, None, start_line, start_col)
        elif current_char == ")":
            self.advance(1)
            return Token(RPAREN, None, start_line, start_col)
        elif current_char == "{":
            self.advance(1)
            return Token(LBRACE, None, start_line, start_col)
        elif current_char == "}":
            self.advance(1)
            return Token(RBRACE, None, start_line, start_col)
        elif current_char == "/":
            self.advance(1)
            return Token(DIV, None, start_line, start_col)
        elif current_char == ",":
            self.advance(1)
            return Token(COMMA, None, start_line, start_col)
        elif current_char == "<":
            self.advance(1)
            return Token(LESS_THAN, None, start_line, start_col)
        elif current_char == ">":
            self.advance(1)
            return Token(GREATER_THAN, None, start_line, start_col)
        elif current_char == '"':
            self.advance(1)
            value = ""
            while (
                self.get_current_char() is not None and self.get_current_char() != '"'
            ):

                if self.get_current_char() == "\\":
                    self.advance()
                    match self.get_current_char():
                        case "n":
                            value += "\n"
                        case "t":
                            value += "\t"
                        case _: 
                            value += self.get_current_char() # pyright: ignore[reportOperatorIssue]
                else:
                    value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.advance()
            if self.get_current_char() != '"':
                raise SyntaxError("Unterminated string literal")
            self.advance()
            return Token(STRING, value, start_line, start_col)

        elif current_char.isalpha() or current_char == "_":
            to_return = current_char
            self.advance()
            while (
                self.get_current_char() is not None
                and self.get_current_char().isalnum()  # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char() == "_"
            ):  # pyright: ignore[reportOptionalMemberAccess]
                to_return += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.advance()
            tok_type = KEYWORDS.get(to_return, IDENTIFIER)
            return Token(tok_type, to_return, start_line, start_col)

        raise SyntaxError(f'Unexpected token "{current_char}"')


class Parser:
    def __init__(self, tokens: list[Token], base_env: list[tuple]):
        self.base_env = base_env
        self.tokens = tokens
        self.pos = 0
        if self.tokens:
            self.current_token = self.tokens[0]
        else:
            self.current_token = Token(EOF, None, 0, 0)

    def eat(self, token_type):
        if self.current_token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {self.current_token.type}")
        self.advance()

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(EOF, None, 0, 0)

    def arithmetic_expr(self):
        node = self.term()
        while self.current_token and self.current_token.type in (ADD, SUB):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.term())
        return node
    def expr(self):
        node = self.logical_and()
        while self.current_token.type == OR:
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.logical_and())
        
        return node
    def logical_and(self):
        node = self.equality()
        while self.current_token.type == AND:
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.equality())
        return node
    def comparison(self):
        node = self.arithmetic_expr()
        while self.current_token.type in (LT, GT, LTE, GTE):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.arithmetic_expr())
        return node
    
    def equality(self):
        node = self.comparison()
        while self.current_token.type in (EQUAL_TO, NOT_EQUAL_TO):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.comparison())
        return node
    def term(self):
        node = self.power()
        while self.current_token and self.current_token.type in (MUL, DIV):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(self.current_token.line, node, op, self.power())
        return node

    def power(self):
        node = self.factor()
        if self.current_token and self.current_token.type == POW:
            op = self.current_token.type
            self.eat(POW)
            node = BinOp(self.current_token.line, node, op, self.power())  # right-associative
        return node
    def factor(self):
        token = self.current_token
        if token.type == SUB:
            self.eat(SUB)
            return UnaryOp(token.line, NEG, self.factor())
        return self.postfix()
    def postfix(self):
        node = self.primary()

        # Handle dots first
        while self.current_token.type == DOT:
            dot_line = self.current_token.line
            self.eat(DOT)
            if self.current_token.type != IDENTIFIER:
                raise SyntaxError("Expected identifier after '.'")
            name = self.current_token.value
            self.eat(IDENTIFIER)
            node = Attribute(dot_line, node, name)

        # Then handle function calls
        while self.current_token.type == LPAREN:
            call_line = self.current_token.line
            self.eat(LPAREN)
            args = []
            if self.current_token.type != RPAREN:
                args.append(self.expr())
                while self.current_token.type == COMMA:
                    self.eat(COMMA)
                    args.append(self.expr())
            if self.current_token.type == EOF:
                raise IncompleteInput
            self.eat(RPAREN)
            node = Call(call_line, node, args)
        return node
    def primary(self):
        token = self.current_token
        if token.type == INT:
            self.eat(INT)
            return Number(token.line, token.value)
        elif token.type == LBRACKET:
            if self.current_token.type == EOF:
                raise IncompleteInput
            self.eat(LBRACKET)
            items = []
            if self.current_token.type != RBRACKET:
                if self.current_token.type == EOF:
                    raise IncompleteInput
                items.append(self.expr())
                while self.current_token.type == COMMA:
                    self.eat(COMMA)
                    if self.current_token.type == EOF:
                        raise IncompleteInput
                    items.append(self.expr())
            self.eat(RBRACKET)
            return Array(token.line, items)
        elif token.type == FLOAT:
            self.eat(FLOAT)
            return Float(token.line, token.value)
        elif token.type == STRING:
            self.eat(STRING)
            return String(token.line, token.value)
        elif token.type == BOOL:
            self.eat(BOOL)
            return Bool(token.line, token.value)
        elif token.type == IDENTIFIER:
            self.eat(IDENTIFIER)
            return Variable(token.line, token.value)
        elif token.type == LPAREN:
            self.eat(LPAREN)
            node = self.expr()
            if self.current_token.type == EOF:
                raise IncompleteInput
            self.eat(RPAREN)
            return node
        raise SyntaxError(f"Unexpected token {token}")
    def export(self):
        self.eat(EXPORT)
        out = self.statement()
        if not isinstance(out, Assign):
            raise RuntimeError("Cannot export anything other than an assignment or function")
        name = out.name
        ln = out.line
        return Export(ln, out.value, name)
    def statement(self):
        while self.current_token.type == NEWLINE:
            self.eat(NEWLINE)

        if self.current_token.type == RBRACE:
            return None
        elif self.current_token.type == LBRACE:
            return self.block()
        elif self.current_token.type == FUNC:
            return self.function_decl()
        elif self.current_token.type == IF:
            return self.if_decl()
        elif self.current_token.type == EXPORT:
            return self.export()
        elif self.current_token.type == WHILE:
            return self.while_decl()
        elif self.current_token.type == IMPORT:
            ln = self.current_token.line
            self.eat(IMPORT)
            name = self.current_token.value
            self.eat(IDENTIFIER)
            base_path = os.curdir
            for i, item in enumerate(self.base_env):
                if isinstance(item[1], BuiltinModule) and item[1].name == name:
                    return Assign(-1, name, BuiltinModulePointer(ln, i))
            if f"{name}.ls" in os.listdir("packages"):
                modpath = os.path.join(base_path, "packages", f"{name}.ls")
            elif f"{name}.ls" in os.listdir():
                modpath = os.path.join(base_path, f"{name}.ls")
            else:
                raise RuntimeError(f"Can't find module {name}")
            with open(modpath) as f:
                content = f.read()
                
            tknr = Tokenizer(content)
            tkns = []
            while True:
                tkn = tknr.get_next_token()
                tkns.append(tkn)
                if tkn.type == EOF:
                    break
            psr = Parser(tkns, self.base_env)
            program = psr.program()
            mod = Module(self.current_token.line, program, name)
            return Assign(self.current_token.line, name, mod)
        elif self.current_token.type == RETURN:
            self.eat(RETURN)
            if self.current_token.type in (NEWLINE, RBRACE):
                return Return(self.current_token.line, None)
            value = self.expr()
            return Return(self.current_token.line, value)
        elif self.current_token.type == IDENTIFIER:
            next_tok = self.peek()
            if next_tok and next_tok.type == ASSIGN:
                name = self.current_token.value
                self.eat(IDENTIFIER)
                self.eat(ASSIGN)
                value = self.expr()
                return Assign(self.current_token.line, name, value)
        return self.expr()
    def if_decl(self):
        self.eat(IF)
        if self.current_token.type == EOF:
            raise IncompleteInput
        expr = self.expr()
        if self.current_token.type == EOF:
            raise IncompleteInput
        body = self.block()
        if self.current_token.type == ELSE and self.peek().type == IF:
            self.eat(ELSE)
            else_body = self.if_decl()
        elif self.current_token.type == ELSE:
            self.eat(ELSE)
            else_body = self.block()
        else:
            else_body = None
        return If(self.current_token.line, expr, body, else_body)
    def while_decl(self):
        self.eat(WHILE)
        if self.current_token.type == EOF:
            raise IncompleteInput
        expr = self.expr()
        if self.current_token.type == EOF:
            raise IncompleteInput
        body = self.block()
        return While(self.current_token.line, expr, body)
    def function_decl(self):
        self.eat(FUNC)

        name = self.current_token.value
        self.eat(IDENTIFIER)

        self.eat(LPAREN)
        params = []

        if self.current_token.type == IDENTIFIER:
            params.append(self.current_token.value)
            self.eat(IDENTIFIER)
            while self.current_token.type == COMMA:
                self.eat(COMMA)
                params.append(self.current_token.value)
                self.eat(IDENTIFIER)
        self.eat(RPAREN)

        body = self.block()
        return Assign(self.current_token.line, name, Function(self.current_token.line, params, body))

    def peek(self):
        idx = self.pos + 1
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(EOF, None, 0, 0)

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

    def block(self):
        self.eat(LBRACE)
        statements = []

        while self.current_token.type != RBRACE:
            if self.current_token.type == EOF:
                raise IncompleteInput
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
        if self.current_token.type == EOF:
            raise IncompleteInput
        self.eat(RBRACE)
        return Block(self.current_token.line, statements)


    
class Array(ASTNode):
    def __init__(self, line, items:list[ASTNode]):
        self.line = line
        self.items = items
    def __repr__(self):
        return f"Array({self.items})"
class Block(ASTNode):
    def __init__(self, line, statements:list[ASTNode]):
        self.statements = statements
        self.line = line
    def __repr__(self):
        return f"Block({self.statements})"




class Number(ASTNode):
    def __init__(self, line, value: int):
        self.value = value
        self.line = line

    def __repr__(self) -> str:
        return f"Number({self.value})"
class Float(ASTNode):
    def __init__(self, line, value: int):
        self.value = value
        self.line = line

    def __repr__(self) -> str:
        return f"Number({self.value})"

class Bool(ASTNode):
    def __init__(self, line, value:bool):
        self.value = value
        self.line = line
    def __repr__(self) -> str:
        return f"Bool({self.value})"

class Call(ASTNode):
    def __init__(self, line, func:  ASTNode, args: list):
        self.func = func
        self.args = args
        self.line = line

    def __repr__(self) -> str:
        return f"Call({self.func}, {self.args})"
class Attribute(ASTNode):
    def __init__(self, line, lhs, rhs):
        self.lhs: ASTNode = lhs
        self.rhs:str = rhs
        self.line = line

    def __repr__(self) -> str:
        return f"Attribute({self.lhs}, {self.rhs})"

class UnaryOp(ASTNode):
    def __init__(self, line, op: str, right: ASTNode):
        self.op = op
        self.right = right
        self.line = line

    def __repr__(self) -> str:
        return f"BinOp({self.op}, {self.right})"


class BinOp(ASTNode):
    def __init__(self, line, left: ASTNode, op: str, right: ASTNode):
        self.op = op
        self.left = left
        self.right = right
        self.line = line

    def __repr__(self) -> str:
        return f"BinOp({self.left}, {self.op}, {self.right})"


class Variable(ASTNode):
    def __init__(self, line, name: str):
        self.name = name
        self.line = line

    def __repr__(self):
        return f"Variable({self.name})"


class Assign(ASTNode):
    def __init__(self, line, name: str, value: ASTNode):
        self.name = name
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Assign({self.name}, {self.value})"




class UserFunction(Call):
    def __init__(self, line, params, body, closure):
        self.params = params
        self.body = body
        self.closure = closure
        self.line = line

    def __repr__(self):
        return f"UserFunction({self.params}, {self.body}, {self.closure})"


class String(ASTNode):
    def __init__(self, line, value):
        self.value = value
        self.line = line

    def __repr__(self):
        return f"String({self.value})"


class Return(ASTNode):
    def __init__(self, line, value):
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Return({self.value})"


class Function(ASTNode):
    def __init__(self, line, params, body):
        self.params = params
        self.body = body
        self.line = line

    def __repr__(self):
        return f"Function({self.params}, {self.body})"

class If(ASTNode):
    def __init__(self, line, expr:ASTNode, body:Block, else_body:Block | None):
        self.expr = expr
        self.body = body
        self.else_body = else_body
        self.line = line

    def __repr__(self):
        return f"If({self.expr}, {self.body}, {self.else_body})"
class While(ASTNode):
    def __init__(self, line, expr:ASTNode, body:Block):
        self.expr = expr
        self.body = body
        self.line = line

    def __repr__(self):
        return f"If({self.expr}, {self.body})"

class Export(ASTNode):
    def __init__(self, line:int , lhs: ASTNode, name: str):
        self.lhs = lhs
        self.name = name
        self.line = line

    def __repr__(self):
        return f"Export({self.lhs}, {self.name})"


class NOP(ASTNode):
    pass
def eval_ast(node: ASTNode, env: Environment): #DEPRECATED
    if isinstance(node, NOP):
        pass
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

        if isinstance(fn, BuiltinFunction) or type(fn):
            return fn(*args)
        if isinstance(fn, UserFunction):
            call_env = Environment(parent=fn.closure)

            for name, value in zip(fn.params, args):
                call_env.set(name, value)

            return eval_ast(fn.body, call_env)
        raise SyntaxError(f"{type(fn).__name__} is not callable")
    if isinstance(node, Variable):
        return env.get(node.name)
    if isinstance(node, Assign):
        value = eval_ast(node.value, env)
        env.set(node.name, value)
        return value
    if isinstance(node, String):
        return node.value
    if isinstance(node, Block):
        local_env = Environment(parent=env)
        result = None
        try:
            for stmt in node.statements:
                result = eval_ast(stmt, local_env)
        except ReturnSignal as r:
            return r.value
        return result
    if isinstance(node, Function):
        return UserFunction(
            node.line,
            node.params,
            node.body,
            env,  # capture closure
        )
    if isinstance(node, Return):
        raise ReturnSignal(eval_ast(node.value, env))
    if isinstance(node, Bool):
        return node.value
    if isinstance(node, If):
        if eval_ast(node.expr, env):
            return eval_ast(node.body, env)
        elif node.else_body:
            return eval_ast(node.else_body, env)
        else:
            return NOP()
        
    raise RuntimeError(f"Unknown node {node}")


OP_SET_VAR = "STORE"
OP_GET_VAR = "RETRIEVE"
OP_PUSH_CONST = "PUSH_CONST"
OP_ADD = ADD
OP_SUB = SUB
OP_MUL = MUL
OP_DIV = DIV
OP_POW = POW
OP_GT = GT
OP_GTE = GTE
OP_LT = LT
OP_LTE = LTE
OP_EQUAL_TO = EQUAL_TO
OP_NOT_EQUAL_TO = NOT_EQUAL_TO
OP_OR = OR
OP_AND = AND
OP_CALL = "CALL"
NEG = "NEG"
OP_NEG = NEG
OPCODE_MAP = {
    ADD: OP_ADD,
    SUB: OP_SUB,
    MUL: OP_MUL,
    DIV: OP_DIV,
    POW: OP_POW,
    LT: OP_LT,
    GT: OP_GT,
    GTE: OP_GTE,
    LTE: OP_LTE,
    EQUAL_TO: OP_EQUAL_TO,
    NOT_EQUAL_TO: OP_NOT_EQUAL_TO,
    OR: OP_OR,
    AND: OP_AND,
    NEG: OP_NEG
}
BUILTIN = "BUILTIN"
NULL = "NULL"
class Scope():
    def __init__(self, var_map={}, args = {}):
        self.var_map: dict = var_map

        self.next_local = len(var_map)
        self.args = args
    def __repr__(self):
        return f"Scope({self.var_map}, {self.next_local})"
class Compiler():
    def __init__(self, env: list, ASTenv):
        self.constants = []
        self.vars = []
        self.var_map = {}
        self.const_map = {}
        self.code = []
        self.passed_env = env
        self.scopes:list[Scope] = []
        self.var_count = 0
        self.ASTenv = ASTenv
        self.lines = []
        self.modules = []
        self.exports = []
        self.enter_scope()
        

    def enter_scope(self, var_map={}, args={}):
        self.scopes.append(Scope(var_map, args))
    def exit_scope(self):
        self.scopes.pop()
    def add_constant(self, value:tuple | list) -> int:
        value_tuple = tuple(value)
        if value_tuple in self.const_map:
            return self.const_map[value_tuple]
        index = len(self.constants)
        self.constants.append(value_tuple)
        self.const_map[value_tuple] = index
        return index
    def declare_local(self, name):
        scope = self.scopes[-1]
        if name in scope.var_map:
            return scope.var_map[name]
        index = scope.next_local
        scope.var_map[name] = index
        scope.next_local += 1
        self.var_count+=1
        return index
    def get_var(self, name):
        # walk outward for nested scopes (later)
        for depth, scope in enumerate(reversed(self.scopes)):
            if name in scope.var_map:
                return scope.var_map[name], 'user', depth
        for i, item in enumerate(self.passed_env):
            if item == name:
                return i, "builtin", None
        return None
    def emit(self, line:int, opcode, *operands):
        idx = len(self.code)
        self.code.append((opcode, *operands))
        self.lines.append(line)
        return idx
    def compile(self, program:Program, features = [], input_source: str | None = None) -> list[str]:
        if input_source is None and "source" in features:
            raise RuntimeError("Compiler needs input source to compile with source info.")
        for node in program.statements:
            self.compile_ins(node)
        self.emit(0,"NOP")
        output = []
        output.append(".version")
        output.append("ENV 1")
        output.append("ISA 1")
        output.append(f".frame {self.scopes[-1].next_local}")

        output.append(".const")
        for const in self.constants:
            output.append(f'{const[0]}"{str(const[1]).replace("\n", "\\n").replace(r"\\", r"\\")}"')
        output.append(".code")
        for instr in self.code:
            output.append(" ".join(map(str, instr)))
        if "lines" in features:
            output.append(".line")
            for line in self.lines:
                output.append(line)
        if "source" in features:
            output.append(".source")
            output += input_source.split("\n") # pyright: ignore[reportOptionalMemberAccess]
        return output
    def compile_ins(self, node:ASTNode, *other):
        if isinstance(node, String):
            idx = self.add_constant([TYPES[STRING], node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Number):
            idx = self.add_constant([TYPES[INT], node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Float):
            idx = self.add_constant([TYPES[FLOAT], node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)

        elif isinstance(node, Variable):
            #if node.name in self.scopes[-1].var_map:
                idx = self.get_var(node.name)
                if idx is None:
                    raise RuntimeError(f"Variable {node.name} not declared")
                if idx[1] == 'user':
                    self.emit(node.line, OP_GET_VAR, idx[0], idx[2]) # RETRIEVE idx depth
                else:
                    self.emit(node.line, "PUSH_BUILTIN", idx[0])
        elif isinstance(node, Assign) and isinstance(node.value, Function):
            res = self.get_var(node.name)
            if res is None:
                idx = self.declare_local(node.name)
                self.compile_ins(node.value, node.name)
                self.emit(node.line, OP_SET_VAR, idx, 0)
            else:
                idx, cat, depth = res
                if cat == "builtin":
                    raise RuntimeError("Attempted to assign a value to a builtin")
                self.compile_ins(node.value, node.name)
                idx = self.declare_local(node.name)
                self.emit(node.line, OP_SET_VAR, idx, depth)
                warn(f"Reassignment to a function attempted for {node.name} on {node.line}. This is usually not recommended.")
        elif isinstance(node, Assign):
            res = self.get_var(node.name)
            if res is None:
                self.compile_ins(node.value)
                idx = self.declare_local(node.name)
                self.emit(node.line, OP_SET_VAR, idx, 0)
            else:
                idx, cat, depth = res
                if cat == "builtin":
                    raise RuntimeError("Attempted to assign a value to a builtin")
                self.compile_ins(node.value)
                idx = self.declare_local(node.name)
                self.emit(node.line, OP_SET_VAR, idx, depth)
        elif isinstance(node, BuiltinModulePointer):
            ref = self.ASTenv[node.idx]
            if ref[0] in self.modules:
                raise RuntimeError(f"Module {ref[0]} already imported.")
            self.emit(-1, "PUSH_BUILTIN", node.idx)
        elif isinstance(node, Module):
            if node.name in self.modules:
                raise RuntimeError(f"Module {node.name} already imported.")
            self.modules.append(node.name)
            self.scopes.append(Scope())
            for statement in node.body.statements:
                self.compile_ins(statement)
            self.scopes.pop()
            self.emit(node.line, "MAKE_MODULE")
        elif isinstance(node, BinOp):
            self.compile_ins(node.left)
            self.compile_ins(node.right)
            self.emit(node.line,OPCODE_MAP[node.op])
        elif isinstance(node, UnaryOp):
            self.compile_ins(node.right)
            self.emit(node.line, OPCODE_MAP[node.op])
        elif isinstance(node, Block):
            for statement in node.statements:
                self.compile_ins(statement)
        elif isinstance(node, Bool):
            idx = self.add_constant([TYPES[BOOL], "true" if node.value else "false"])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Call):
            self.compile_ins(node.func)
            for arg in node.args:
                self.compile_ins(arg)
            self.emit(node.line, OP_CALL, len(node.args))
        elif isinstance(node, While):
            self.compile_ins(node.expr)
            jmp = self.emit(node.line, "JMPIFF", None)
            self.compile_ins(node.body)
            self.compile_ins(node.expr)
            self.emit(node.line, "JMPIF", jmp+1)
            self.code[jmp] = ("JMPIFF", len(self.code))
        elif isinstance(node, If):
            self.compile_ins(node.expr)
            jmp = self.emit(node.line, "JMPIFF", None)
            self.compile_ins(node.body)
            if node.else_body:
                jmp2 = self.emit(node.line, "JMP", None)
                self.code[jmp] = ("JMPIFF", len(self.code))
                self.compile_ins(node.else_body)
                self.code[jmp2] = ("JMP",len(self.code))
            else:
                self.code[jmp] = ("JMPIFF", len(self.code))
        elif isinstance(node, Array):
            for item in node.items:
                self.compile_ins(item)
            self.emit(node.line, "BUILD_ARRAY", len(node.items))
        elif isinstance(node, NOP):
            self.emit(0,"NOP")
        elif isinstance(node, Function):
            jmp  = self.emit(node.line, "JMP", None)
            fn_entry = len(self.code)
            self.enter_scope({})

            for param in node.params:
                self.declare_local(param)
            self.compile_ins(node.body)

            self.emit(node.line, "PUSH_CONST", self.add_constant((base_env.T_NULL, None)))
            self.emit(node.line,"RET")

            local_count = self.scopes[-1].next_local
            self.exit_scope()
            self.code[jmp] = ("JMP", len(self.code))
            if len(other) >= 1:
                idx = self.add_constant([2, other[0]])
                self.emit(node.line, "MAKE_FUNCTION", fn_entry, local_count, len(node.params), idx)
            else:
                raise RuntimeError("(internal) Expected array `other` to have at least 1 value, found 0")
        elif isinstance(node, Return):
            self.compile_ins(node.value)
            self.emit(node.line, "RET")
        elif isinstance(node, Export):
            self.compile_ins(node.lhs, node.name)
            idx = self.add_constant((2, node.name))
            self.emit(node.line, "EXPORT", idx)
        elif isinstance(node, Attribute):
            self.compile_ins(node.lhs)
            idx = self.add_constant((2, node.rhs))
            self.emit(node.line, "GETATTR", idx)
        else:
            raise NotImplementedError(f"Did not implement {node} yet :<")
