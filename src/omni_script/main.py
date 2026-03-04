from dataclasses import dataclass
from typing import Any, Collection, Generator, Literal
from omni_script import base_env
from omni_script.runtime import (
    T_BOOL,
    T_FLOAT,
    T_INT,
    T_NULL,
    T_STRING,
    BuiltinFunction,
    Module,
    ASTNode,
    Program,
    BuiltinModule,
    BuiltinModulePointer,
    Builtin,
)
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
AT_RATE = "AT_RATE"
NOT = "NOT"


class CompilationException(Exception):
    code: int
    msg: str
    line: int | None
    col: int | None


@dataclass
class ParserError(CompilationException):
    code: int  # TODO: Formalize these
    msg: str
    line: int | None
    col: int | None  # TODO: Actually use columns (also in Tokens)


@dataclass
class CompilerError(CompilationException):
    code: int
    msg: str
    line: int | None
    col: int | None


@dataclass
class TokenizerError(CompilationException):
    code: int
    msg: str
    line: int | None
    col: int | None


KEYWORDS = {
    "func": FUNC,
    "return": RETURN,
    "if": IF,
    "else": ELSE,
    "or": OR,
    "and": AND,
    "while": WHILE,
    "import": IMPORT,
    "export": EXPORT,
    "@": AT_RATE,
    "not": NOT,
}


class Callable:
    pass


class IncompleteInput(Exception):
    pass


@dataclass
class Token:
    type: str
    value: Any
    line: int
    col: int


class Tokenizer:
    def __init__(self, string: str):
        self.string: str = string
        self.current_idx: int = 0
        self.line: int = 0
        self.col: int = 0

    def advance(self, steps: int = 1) -> str | None:
        if steps <= 0:  # To make sure that `ch` isn't `Unbound`
            return self.get_current_char()
        for _ in range(steps):
            ch = self.get_current_char()
            if ch is None:
                return None
            self.current_idx += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return ch  # pyright: ignore reportPossiblyUnboundVariable

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
        return self.string[self.current_idx : end] == text

    def get_next_token(self):  # sourcery skip: extract-method, low-code-quality
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
                and self.get_current_char().isdigit()  # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char()
                == "."  # pyright: ignore[reportOptionalMemberAccess]
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
        elif current_char == "@":
            self.advance(1)
            return Token(AT_RATE, None, start_line, start_col)
        elif current_char == "#":
            while (
                self.get_current_char() is not None and self.get_current_char() != "\n"
            ):
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
        elif self.check("!="):
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
                            value += (
                                self.get_current_char()
                            )  # pyright: ignore[reportOperatorIssue]
                else:
                    value += (
                        self.get_current_char()
                    )  # pyright: ignore[reportOperatorIssue]
                self.advance()
            if self.get_current_char() != '"':
                raise TokenizerError(
                    1, "Unterminated string literal", self.line, self.col
                )
            self.advance()
            return Token(STRING, value, start_line, start_col)
        elif current_char == "'":
            self.advance(1)
            value = ""
            while (
                self.get_current_char() is not None and self.get_current_char() != "'"
            ):
                if self.get_current_char() == "\\":
                    self.advance()
                    match self.get_current_char():
                        case "n":
                            value += "\n"
                        case "t":
                            value += "\t"
                        case _:
                            value += (
                                self.get_current_char()
                            )  # pyright: ignore[reportOperatorIssue]
                else:
                    value += (
                        self.get_current_char()
                    )  # pyright: ignore[reportOperatorIssue]
                self.advance()
            if self.get_current_char() != "'":
                raise TokenizerError(
                    1, "Unterminated string literal", self.line, self.col
                )
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
                to_return += (
                    self.get_current_char()
                )  # pyright: ignore[reportOperatorIssue]
                self.advance()
            tok_type = KEYWORDS.get(to_return, IDENTIFIER)
            return Token(tok_type, to_return, start_line, start_col)

        raise TokenizerError(
            2, f'Unexpected character "{current_char}"', self.line, self.col
        )


@dataclass
class OmniType:
    display: str | None = None

    @classmethod
    def try_from(cls, s: str):
        # Iterate over all subclasses of OmniType
        for subclass in cls.__subclasses__():
            instance = subclass()  # create an instance
            if instance.display == s:
                return instance
        raise ValueError(f"No OmniType subclass with display='{s}' found")


@dataclass
class OmniStr(OmniType):
    def __init__(self):
        self.display = "str"


@dataclass
class OmniFloat(OmniType):
    def __init__(self):
        self.display = "float"


@dataclass
class OmniInt(OmniType):
    def __init__(self):
        self.display = "int"


@dataclass
class OmniFunc(OmniType):
    def __init__(self):
        self.display = "func"


@dataclass
class OmniModule(OmniType):
    def __init__(self):
        self.display = "mod"


@dataclass
class OmniArray(OmniType):
    def __init__(self):
        self.display = "array"


@dataclass
class OmniNull(OmniType):
    def __init__(self):
        self.display = "null"


class Parser:
    def __init__(self, tokens: list[Token], base_env: list[tuple], repl: bool=False):
        self.base_env = base_env
        self.tokens = tokens
        self.pos = 0
        self.repl = repl
        self.current_token = self.tokens[0] if self.tokens else Token(EOF, None, 0, 0)
        
    def incomplete_input(self):
        if self.repl:
            raise IncompleteInput
    def eat(self, token_type):
        out = self.current_token
        if self.current_token.type != token_type:
            raise ParserError(
                3,
                f"Expected {token_type}, got {self.current_token.type}",
                self.current_token.line,
                self.current_token.col,
            )
        self.advance()
        return out

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

    def logical_not(self):
        if self.current_token.type == NOT:
            self.eat(NOT)
            return UnaryOp(self.current_token.line, NOT, self.logical_not())
        return self.equality()

    def logical_and(self):
        node = self.logical_not()
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
            node = BinOp(
                self.current_token.line, node, op, self.power()
            )  # right-associative
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
                raise ParserError(
                    4,
                    "Expected identifier after '.'",
                    self.current_token.line,
                    self.current_token.col,
                )
            name = self.eat(IDENTIFIER).value
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
                self.incomplete_input()
            self.eat(RPAREN)
            node = Call(call_line, node, args)

        while self.current_token.type == LBRACKET:
            ln = self.current_token.line
            self.eat(LBRACKET)
            idx = self.expr()
            self.eat(RBRACKET)
            node = GetIndex(ln, node, idx)
        return node

    def skip_newline(self):
        while self.current_token.type == NEWLINE:
            self.eat(NEWLINE)

    def primary(self):
        token = self.current_token
        if token.type == INT:
            self.eat(INT)
            return Number(token.line, token.value)
        elif token.type == LBRACKET:
            self.eat(LBRACKET)
            if self.current_token.type == EOF:
                self.incomplete_input()
            if self.current_token.type == NEWLINE:
                self.eat(NEWLINE)
            items = []
            if self.current_token.type != RBRACKET:
                if self.current_token.type == EOF:
                    self.incomplete_input()
                self.skip_newline()
                items.append(self.expr())
                while self.current_token.type == COMMA:
                    self.eat(COMMA)
                    if self.current_token.type == EOF:
                        self.incomplete_input()
                    self.skip_newline()
                    items.append(self.expr())
                self.skip_newline()
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
                self.incomplete_input()
            self.skip_newline()
            self.eat(RPAREN)
            return node
        raise ParserError(
            3,
            f"Unexpected token {token.type}{f' `{token.value}`' if token.value is not None else ''}",
            self.current_token.line,
            self.current_token.col,
        )

    def export(self):
        self.eat(EXPORT)
        out = self.statement()
        if not isinstance(out, Assign):
            raise ParserError(
                5,
                "Cannot export anything other than an assignment or function",
                getattr(out, "line", None),
                getattr(out, "col", None),
            )
        name = out.name
        ln = out.line
        return Export(ln, out.value, name)

    def statement(self):
        while self.current_token.type == NEWLINE:
            self.eat(NEWLINE)

        if self.current_token.type == RBRACE:
            return None
        elif self.current_token.type == AT_RATE:
            self.eat(AT_RATE)
            if self.current_token.value == "require":
                ln = self.current_token.line
                self.eat(IDENTIFIER)
                reqs = []
                req = ""

                req += self.eat(IDENTIFIER).value
                
                while self.current_token.type == DOT:
                    req += "."
                    self.eat(DOT)
                    req += self.eat(IDENTIFIER).value
                    
                reqs.append(req)
                req = ""
                while self.current_token.type == COMMA:
                    if self.current_token.type == EOF:
                        self.incomplete_input()
                    self.skip_newline()
                    self.eat(COMMA)
                    req += self.eat(IDENTIFIER).value
                    while self.current_token.type == DOT:
                        req += "."
                        self.eat(DOT)
                        req += self.eat(IDENTIFIER).value
                    reqs.append(req)
                    req = ""
                if self.current_token.type == LBRACE:
                    blk = self.block()
                    else_block: Block | None = None
                    if self.current_token.type == ELSE:
                        self.eat(ELSE)
                        else_block = self.block()
                    return RequireStatement(ln, reqs, blk, else_block)
                else:
                    return BareRequire(ln, reqs)
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
            name = self.eat(IDENTIFIER).value
            base_path = os.curdir
            for i, item in enumerate(self.base_env):
                if isinstance(item[1], BuiltinModule) and item[1].name == name:
                    return Assign(-1, name, BuiltinModulePointer(ln, i))
            if f"{name}.om" in os.listdir(
                "packages"
            ):  # TODO: do this in a more dynamic way
                modpath = os.path.join(base_path, "packages", f"{name}.om")
            elif f"{name}.om" in os.listdir():
                modpath = os.path.join(base_path, f"{name}.om")
            else:
                raise ParserError(
                    6,
                    f"Can't find module {name}",
                    self.current_token.line,
                    self.current_token.col,
                )
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
                name = self.eat(IDENTIFIER).value
                self.eat(ASSIGN)
                value = self.expr()
                return Assign(self.current_token.line, name, value)
        return self.expr()

    def if_decl(self):
        self.eat(IF)
        expr = self.expr()
        if self.current_token.type == EOF:
            self.incomplete_input()
        self.skip_newline()
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
        expr = self.expr()
        if self.current_token.type == EOF:
            self.incomplete_input()
        self.skip_newline()
        body = self.block()
        return While(self.current_token.line, expr, body)

    def function_decl(self):
        ln = self.current_token.line
        self.eat(FUNC)

        name = self.eat(IDENTIFIER).value

        self.eat(LPAREN)
        params: list[FunctionParameter] = []
        optional = False
        if self.current_token.type == IDENTIFIER:
            params.append(
                FunctionParameter(
                    self.current_token.line, self.eat(IDENTIFIER).value, None
                )
            )
            
            if self.current_token.type == ASSIGN:
                optional = True
                self.eat(ASSIGN)
                params[-1].option = self.primary()
            elif optional:
                raise ParserError(
                    7,
                    "Cannot have a non-optional argument after an optional argument",
                    self.current_token.line,
                    self.current_token.col,
                )
            while self.current_token.type == COMMA:
                self.eat(COMMA)
                params.append(
                    FunctionParameter(
                        self.current_token.line, self.eat(IDENTIFIER).value, None
                    )
                )
                if self.current_token.type == ASSIGN:
                    optional = True
                    self.eat(ASSIGN)
                    params[-1].option = self.primary()
                elif optional:
                    raise ParserError(
                        7,
                        "Cannot have a non-optional argument after an optional argument",
                        self.current_token.line,
                        self.current_token.col,
                    )
        self.eat(RPAREN)

        body = self.block()
        return Assign(
            ln,
            name,
            Function(ln, params, body),
        )

    def peek(self):
        idx = self.pos + 1
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(EOF, None, 0, 0)

    def parse(self):
        node = self.statement()
        if self.current_token.type != EOF:
            raise ParserError(
                3,
                f"Unexpected token of type {self.current_token.type}: {self.current_token.value}",
                self.current_token.line,
                self.current_token.col,
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
                self.incomplete_input()
            stmt = self.statement()
            if stmt is not None:
                statements.append(stmt)
        if self.current_token.type == EOF:
            self.incomplete_input()
        self.eat(RBRACE)
        return Block(self.current_token.line, statements)


@dataclass
class BareRequire(ASTNode):
    line: int
    reqs: list[str]


@dataclass
class Array(ASTNode):
    line: int
    items: list[ASTNode]


@dataclass
class GetIndex(ASTNode):
    line: int
    item: ASTNode
    idx: ASTNode


@dataclass
class Block(ASTNode):
    line: int
    statements: list[ASTNode]


@dataclass
class RequireStatement(ASTNode):
    line: int
    reqs: list[str]
    statement: Block
    else_block: Block | None


@dataclass
class Number(ASTNode):
    line: int
    value: int


@dataclass
class Float(ASTNode):
    line: int
    value: float


@dataclass
class Bool(ASTNode):
    line: int
    value: bool


@dataclass
class Call(ASTNode):
    line: int
    func: ASTNode
    args: list[ASTNode]


@dataclass
class Attribute(ASTNode):
    line: int
    lhs: ASTNode
    rhs: str


@dataclass
class UnaryOp(ASTNode):
    line: int
    op: str
    right: ASTNode


@dataclass
class BinOp(ASTNode):
    line: int
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class Variable(ASTNode):
    line: int
    name: str


@dataclass
class FunctionParameter(ASTNode):
    line: int
    name: str
    option: None | ASTNode


@dataclass
class Assign(ASTNode):
    line: int
    name: str
    value: ASTNode


@dataclass
class String(ASTNode):
    line: int
    value: str


@dataclass
class Return(ASTNode):
    line: int
    value: ASTNode | None


@dataclass
class Function(ASTNode):
    line: int
    params: list[FunctionParameter]
    body: Block

    def __init__(self, line: int, params, body):
        self.params = params
        self.body = body
        self.line = line

    def __repr__(self):
        return f"Function({self.params}, {self.body})"


@dataclass
class If(ASTNode):
    line: int
    expr: ASTNode
    body: Block
    else_body: Block | None


@dataclass
class While(ASTNode):
    line: int
    expr: ASTNode
    body: Block


@dataclass
class Export(ASTNode):
    line: int
    lhs: ASTNode
    name: str


class NOP(ASTNode):
    pass


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
OP_NOT = NOT
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
    NEG: OP_NEG,
    NOT: OP_NOT,
}
BUILTIN = "BUILTIN"
NULL = "NULL"


class Compiler:
    def __init__(
        self,
        env: list[str],
        ASTenv: list[tuple[str, Builtin]],
        attrs: list[tuple[str, int, int, tuple[tuple[str, str, str], ...] | None]],
    ):
        self.constants = []
        self.vars = []
        self.reqs: list[str] = []
        self.var_map = {}
        self.const_map = {}
        self.code = []
        self.passed_env = env
        self.scopes: list[Compiler.Scope] = []
        self.var_count = 0
        self.ASTenv = ASTenv
        self.lines = []
        self.modules = []
        self.exports = []
        self.req_stack: list[Compiler.RequirementGroup] = (
            []
        )  # LIFO stack for nested @require statements
        self.req_stack_not_allowed: list[Compiler.RequirementGroup] = (
            []
        )  # for errors when using a feature where it isn't allowed, like the else branch of an @require statement
        self.attrs: list[tuple[str, int, int, tuple[tuple[str, str, str], ...] | None]] = attrs
        self.enter_scope()

    @dataclass
    class ScopeItem:
        idx: int
        value: ASTNode

    @dataclass
    class RequirementGroup:  # I'm addicted to classes
        reqs: list[str]

    @dataclass
    class BuiltinScopeItem:
        value: Builtin

    class Scope:
        def __init__(self, var_map={}, args={}):
            self.var_map: dict[str, Compiler.ScopeItem] = var_map

            self.next_local = len(var_map)
            self.args = args

        def __repr__(self):
            return f"Scope({self.var_map}, {self.next_local})"

    @dataclass
    class Warn:
        message: str
        line: int | None
        col: int | None

    @dataclass
    class Result:
        value: str

    def enter_scope(self, var_map={}, args={}):
        self.scopes.append(Compiler.Scope(var_map, args))

    def exit_scope(self):
        self.scopes.pop()

    def add_constant(self, value: tuple[int, Any] | list) -> int:
        value_tuple = tuple(value)
        if value_tuple in self.const_map:
            return self.const_map[value_tuple]
        index = len(self.constants)
        self.constants.append(value_tuple)
        self.const_map[value_tuple] = index
        return index

    def declare_local(self, name: str, value: ASTNode):
        scope = self.scopes[-1]
        if name in scope.var_map:
            return scope.var_map[name].idx

        index = scope.next_local
        scope.var_map[name] = Compiler.ScopeItem(index, value)
        scope.next_local += 1
        self.var_count += 1

        return index

    def get_var(
        self, name
    ) -> tuple[int, Literal["user", "builtin"], int | None] | None:
        for depth, scope in enumerate(reversed(self.scopes)):
            if name in scope.var_map:
                return scope.var_map[name].idx, "user", depth
        for i, item in enumerate(self.passed_env):
            if item == name:
                return i, "builtin", None
        return None

    def get_var_obj(
        self, name: str
    ) -> tuple[ScopeItem, int | None] | tuple[BuiltinScopeItem, None] | None:
        for depth, scope in enumerate(reversed(self.scopes)):
            if name in scope.var_map:
                return scope.var_map[name], depth
        for i, item in enumerate(self.ASTenv):
            if item[0] == name:
                return Compiler.BuiltinScopeItem(item[1]), None
        return None

    def emit(self, line: int, opcode, *operands):
        idx = len(self.code)
        self.code.append((opcode, *operands))
        self.lines.append(line)
        return idx

    def compile(
        self,
        program: Program,
        features: Collection[Literal["source"] | Literal["line"]] = [],
        input_source: str | None = None,
    ) -> Generator[Warn, None, list[str]]:
        if input_source is None and "source" in features:
            raise CompilerError(
                8,
                "Compiler needs input source to compile with source info.",
                None,
                None,
            )
        for node in program.statements:
            # empty statements (e.g. stray braces) may be None
            if node is None:
                continue
            yield from self.compile_ins(node)
            # drop any value produced by the statement so that subsequent
            # instructions start with a clean stack
            self.emit(node.line, "POP")
        self.emit(0, "NOP")
        output = []
        output.append(".version")
        output.append("ENV 1")
        output.append("ISA 1")
        if len(self.reqs) > 0:
            output.append(".reqs " + " ".join([str(x) for x in self.reqs]))

        output.append(f".frame {self.scopes[-1].next_local}")

        output.append(".const")
        for const in self.constants:
            output.append(
                f'{const[0]};{str(const[1]).replace("\n", "\\n").replace(";", "\\;")};'
            )
        output.append(".code")
        for instr in self.code:
            output.append(" ".join(map(str, instr)))
        if "line" in features:
            output.append(".line")
            for line in self.lines:
                output.append(line)
        if "source" in features:
            output.append(".source")
            output += (input_source.splitlines())  # pyright: ignore[reportOptionalMemberAccess]
        return output

    def raise_for_req(
        self, req: str, name: str, second_name: str, node: ASTNode | None, unsure: bool=False
    ):
        if req in self.reqs:
            return
        broken = False
        for item in self.req_stack:
            if req in item.reqs:
                broken = True
                break
        if not broken:
            illegal = False
            for item in self.req_stack_not_allowed:
                if req in item.reqs:
                    illegal = True
            ln = getattr(node, "line", None)
            col = getattr(node, "col", None)
            if illegal:
                if unsure:
                    yield self.Warn(
                        f"CRITICAL: This may need the `{req}` requirement, and is in an illegal zone. Perhaps add `@require {req}` to the top of your program?", #TODO: warning priorities
                        ln,
                        col,
                    )
                else:
                    raise CompilerError(
                        14,
                        f"Attempted using a(n) {name} when it requires `{req}` in an illegal area",
                        ln,
                        col,
                    )
            else:
                if unsure:
                    yield self.Warn(
                        f"This may need the `{req}` requirement. Perhaps add `@require {req}` to the top of your program?",
                        ln,
                        col,
                    )
                else:
                    self.reqs.append(req)
                    yield self.Warn(
                        f"{second_name} implicitly adds the `{req}` requirement. Perhaps add `@require {req}` to the top of your program to make it explicit?",
                        ln,
                        col,
                    )

    def compile_ins(self, node: ASTNode, *other) -> Generator[Warn, None, Any]:
        if isinstance(node, String):
            idx = self.add_constant([T_STRING, node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Number):
            idx = self.add_constant([T_INT, node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Float):
            idx = self.add_constant([T_FLOAT, node.value])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, BareRequire):
            self.reqs += node.reqs
        elif isinstance(node, RequireStatement):
            consts: list[int] = []
            for item in node.reqs:
                consts.append(self.add_constant((2, item)))
            idx = self.emit(node.line, "REQUIRE", *consts, None)
            self.req_stack.append(
                self.RequirementGroup(node.reqs)
            )  # create a new stack so later on warnings wont happen
            yield from self.compile_ins(node.statement)
            self.req_stack.pop()  # remove the stack after the statement
            if node.else_block is not None:
                self.req_stack_not_allowed.append(self.RequirementGroup(node.reqs))
                jmp = self.emit(node.line, "JMP", None)
                self.code[idx] = ("REQUIRE", *consts, len(self.code))
                yield from self.compile_ins(node.else_block)
                self.req_stack_not_allowed.pop()
                self.code[jmp] = ("JMP", len(self.code))
            else:
                self.code[idx] = ("REQUIRE", *consts, len(self.code))
        elif isinstance(node, Variable):
            # if node.name in self.scopes[-1].var_map:
            idx = self.get_var(node.name)
            if idx is None:
                raise CompilerError(
                    9,
                    f"Variable {node.name} not declared",
                    node.line,
                    getattr(node, "col", None),
                )
            if idx[1] == "user":
                self.emit(node.line, OP_GET_VAR, idx[0], idx[2])  # RETRIEVE idx depth
            else:
                self.emit(node.line, "PUSH_BUILTIN", idx[0])
        elif isinstance(node, Assign) and isinstance(node.value, Function):
            res = self.get_var(node.name)
            if res is None:
                idx = self.declare_local(node.name, node.value)
                yield from self.compile_ins(node.value, node.name)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, "DUP")
                self.emit(node.line, OP_SET_VAR, idx, 0)
                return idx, 0
            else:
                idx, cat, depth = res
                yield from self.compile_ins(node.value, node.name)

                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, "DUP")
                self.emit(node.line, OP_SET_VAR, idx, depth)

                yield self.Warn(
                    f"Reassignment to a function attempted for {node.name}. This is usually not recommended",
                    node.line,
                    getattr(node, "col", None),
                )
                return idx, 0
        elif isinstance(node, Assign):
            res = self.get_var(node.name)
            if res is None:
                yield from self.compile_ins(node.value)
                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, "DUP")
                self.emit(node.line, OP_SET_VAR, idx, 0)
            else:
                idx, _, depth = res
                yield from self.compile_ins(node.value)
                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, "DUP")
                self.emit(node.line, OP_SET_VAR, idx, depth)
        elif isinstance(node, BuiltinModulePointer):
            ref = self.ASTenv[node.idx]
            if ref[0] in self.modules:
                raise CompilerError(
                    10,
                    f"Module {ref[0]} already imported.",
                    node.line,
                    getattr(node, "col", None),
                )
            self.emit(-1, "PUSH_BUILTIN", node.idx)
        elif isinstance(node, Module):
            if node.name in self.modules:
                raise CompilerError(
                    10,
                    f"Module {node.name} already imported.",
                    node.line,
                    getattr(node, "col", None),
                )
            self.modules.append(node.name)
            self.scopes.append(Compiler.Scope())
            for statement in node.body.statements:
                yield from self.compile_ins(statement)
            self.scopes.pop()
            self.emit(node.line, "MAKE_MODULE")
        elif isinstance(node, BinOp):
            yield from self.compile_ins(node.left)
            yield from self.compile_ins(node.right)
            self.emit(node.line, OPCODE_MAP[node.op])
        elif isinstance(node, UnaryOp):
            yield from self.compile_ins(node.right)
            self.emit(node.line, OPCODE_MAP[node.op])
        elif isinstance(node, Block):
            for statement in node.statements:
                yield from self.compile_ins(statement)
        elif isinstance(node, Bool):
            idx = self.add_constant([T_BOOL, "true" if node.value else "false"])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Call):
            # compile the expression that identifies the callable (variable, attribute, etc.)
            yield from self.compile_ins(node.func)

            # validate argument count depending on what kind of call this is
            if isinstance(node.func, Variable):
                itm = self.get_var_obj(node.func.name)[0]  # pyright: ignore[reportOptionalSubscript]
                if isinstance(itm, self.ScopeItem):
                    if isinstance(itm.value, Function):
                        params = itm.value.params
                        req: list[FunctionParameter] = []
                        for item in params:
                            if item.option is None:
                                req.append(item)
                        if not (len(req) <= len(node.args) <= len(params)):
                            if not len(req) == len(params):
                                raise CompilerError(
                                    11,
                                    f"Expected {len(req)} to {len(params)} arguments, got {len(node.args)}",
                                    node.line,
                                    getattr(node, "col", None),
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f"Expected exactly {len(req)} arguments, got {len(node.args)}",
                                    node.line,
                                    getattr(node, "col", None),
                                )
                elif isinstance(itm, self.BuiltinScopeItem) and isinstance(
                    itm.value, BuiltinFunction
                ):
                    if itm.value.max_args is None:
                        if not (itm.value.req_args <= len(node.args)):
                            raise CompilerError(
                                11,
                                f"Expected at least {itm.value.req_args} args, got {len(node.args)}",
                                node.line,
                                getattr(node, "col", None),
                            )
                    else:
                        if not (
                            itm.value.req_args <= len(node.args) <= itm.value.max_args
                        ):
                            if itm.value.req_args == itm.value.max_args:
                                raise CompilerError(
                                    11,
                                    f"Expected exactly {itm.value.req_args} args, got {len(node.args)}",
                                    node.line,
                                    getattr(node, "col", None),
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f"Expected {itm.value.req_args} to {itm.value.max_args} args, got {len(node.args)}",
                                    node.line,
                                    getattr(node, "col", None),
                                )
            elif isinstance(node.func, Attribute):
                atr_itm: tuple[str, int, int, tuple[tuple[str, str, str], ...] | None] | None = None
                for item in self.attrs:
                    if item[0] == node.func.rhs:
                        atr_itm = item
                        break
                if atr_itm is None:
                    raise CompilerError(
                        12,
                        f"No attribute `{node.func.rhs}` found",
                        node.line,
                        getattr(node, "col", None),
                    )
                if atr_itm[3] is not None:
                    for item in atr_itm[3]:
                        if len(atr_itm[3]) > 1:
                            yield from self.raise_for_req(item[0], item[1] , item[2], node, True)
                        else:
                            yield from self.raise_for_req(item[0], item[1] , item[2], node, True)
                min_args = atr_itm[1]
                max_args = atr_itm[2]
                if not (min_args <= len(node.args) <= max_args):
                    if min_args == max_args:
                        raise CompilerError(
                            11,
                            f"Expected exactly {min_args} args, got {len(node.args)}",
                            node.line,
                            getattr(node, "col", None),
                        )
                    else:
                        raise CompilerError(
                            11,
                            f"Expected {min_args} to {max_args} args, got {len(node.args)}",
                            node.line,
                            getattr(node, "col", None),
                        )

            # compile argument expressions once
            for arg in node.args:
                yield from self.compile_ins(arg)

            # emit the call instruction appropriate for the kind of callable
            if isinstance(node.func, Variable):
                itm = self.get_var_obj(node.func.name)[0]  # pyright: ignore[reportOptionalSubscript]
                if isinstance(itm, self.ScopeItem):
                    if isinstance(itm.value, Function):
                        params = itm.value.params
                        req: list[FunctionParameter] = []
                        for item in params:
                            if item.option is not None:
                                req.append(item)
                        if len(req) >= len(node.args):
                            for item in params[len(req) :]:
                                yield from self.compile_ins(item.option)  # pyright: ignore[reportArgumentType]
                        self.emit(node.line, OP_CALL, len(params))
                    else:
                        raise  # should not happen
                elif isinstance(itm, self.BuiltinScopeItem):
                    self.emit(node.line, OP_CALL, len(node.args))
                else:
                    raise
            elif isinstance(node.func, Attribute):
                # object + method are on the stack already, just call
                self.emit(node.line, OP_CALL, len(node.args))
            else:
                raise NotImplementedError  # falling back for future call types
        elif isinstance(node, While):
            yield from self.compile_ins(node.expr)
            jmp = self.emit(node.line, "JMPIFF", None)
            yield from self.compile_ins(node.body)
            yield from self.compile_ins(node.expr)
            self.emit(node.line, "JMPIF", jmp + 1)
            self.code[jmp] = ("JMPIFF", len(self.code))
        elif isinstance(node, If):
            yield from self.compile_ins(node.expr)
            jmp = self.emit(node.line, "JMPIFF", None)
            yield from self.compile_ins(node.body)
            if node.else_body:
                jmp2 = self.emit(node.line, "JMP", None)
                self.code[jmp] = ("JMPIFF", len(self.code))
                yield from self.compile_ins(node.else_body)
                self.code[jmp2] = ("JMP", len(self.code))
            else:
                self.code[jmp] = ("JMPIFF", len(self.code))
        elif isinstance(node, Array):
            yield from self.raise_for_req("types.arrays", "Array", 'Arrays', node)
            for item in reversed(node.items):
                yield from self.compile_ins(item)
            self.emit(node.line, "BUILD_ARRAY", len(node.items))
        elif isinstance(node, NOP):
            self.emit(0, "NOP")
        elif isinstance(node, Function):
            jmp = self.emit(node.line, "JMP", None)
            fn_entry = len(self.code)
            self.enter_scope({})
            for param in node.params:
                self.declare_local(param.name, param)
            yield from self.compile_ins(node.body)

            self.emit(
                node.line, "PUSH_CONST", self.add_constant((base_env.T_NULL, None))
            )
            self.emit(node.line, "RET")

            local_count = self.scopes[-1].next_local
            self.exit_scope()
            self.code[jmp] = ("JMP", len(self.code))
            if len(other) >= 1:
                idx = self.add_constant([T_STRING, other[0]])
                self.emit(
                    node.line,
                    "MAKE_FUNCTION",
                    fn_entry,
                    local_count,
                    len(node.params),
                    idx,
                )
            else:
                raise CompilerError(
                    13,
                    "(internal) Expected array `other` to have at least 1 value, found 0. This error should not be raised under any circumstance, please report at https://github.com/DELOLCAT/OmniScript.",
                    None,
                    None,
                )
        elif isinstance(node, Return):
            if node.value is None:
                idx = self.add_constant((T_NULL, ""))
                self.emit(node.line, OP_PUSH_CONST, idx)
                return
            yield from self.compile_ins(node.value)
            self.emit(node.line, "RET")
        elif isinstance(node, Export):
            yield from self.compile_ins(Assign(node.line, node.name, node.lhs), True)
            idx = self.add_constant((T_STRING, node.name))
            self.emit(node.line, "EXPORT", idx)
        elif isinstance(node, Attribute):
            yield from self.raise_for_req("attributes", "Attribute", 'Attributes', node)
            broken = False
            for item in self.attrs:
                if item[0] == node.rhs:
                    broken = True
                    break
            if not broken:
                raise CompilerError(
                    12,
                    f"Could not find attribute {node.rhs}",
                    node.line,
                    getattr(node, "col", None),
                )
            yield from self.compile_ins(node.lhs)
            idx = self.add_constant((T_STRING, node.rhs))
            self.emit(node.line, "GETATTR", idx)
        elif isinstance(node, GetIndex):
            yield from self.raise_for_req("indexes", "Index", "Indexing", node)
            yield from self.compile_ins(node.idx)
            yield from self.compile_ins(node.item)
            self.emit(node.line, "GET_ITEM")
        else:
            raise CompilerError(13, f"Did not implement {node} yet :<", None, None)
