from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Collection, Generator, Literal
from koni_compiler import base_env
from koni_compiler.runtime import (
    T_BOOL,
    T_FLOAT,
    T_INT,
    T_NULL,
    T_STRING,
    BuiltinFunction,
    ASTNode,
    Program,
    Builtin,
)
from enum import Enum, auto


class TokenType(Enum):
    ADD = 'ADD'
    INTEGER = 'INT'
    INT = INTEGER
    IDENTIFIER = 'IDENTIFIER'
    ASSIGN = 'ASSIGN'
    NEWLINE = 'NEWLINE'
    EOF = 'EOF'
    DIVIDE = 'DIV'
    DIV = DIVIDE
    MULTIPLY = 'MUL'
    MUL = MULTIPLY
    POWER = 'POW'
    POW = POWER
    SUBTRACT = 'SUB'
    SUB = SUBTRACT
    RPAREN = 'RPAREN'
    LPAREN = 'LPAREN'
    STRING = 'STRING'
    COMMA = 'COMMA'
    LBRACE = 'LBRACE'
    RBRACE = 'RBRACE'
    FUNC = 'FUNC'
    RETURN = 'RETURN'
    BOOLEAN = 'BOOLEAN'
    BOOL = BOOLEAN
    GREATER_THAN = 'GT'
    GT = GREATER_THAN
    LESS_THAN = 'LT'
    LT = LESS_THAN
    LTE = 'LTE'
    GTE = 'GTE'
    EQUAL_TO = 'EQ'
    NOT_EQUAL_TO = 'NEQ'
    IF = 'IF'
    ELSE = 'ELSE'
    OR = 'OR'
    AND = 'AND'
    FLOAT = 'FLOAT'
    WHILE = 'WHILE'
    DOT = 'DOT'
    IMPORT = 'IMPORT'
    EXPORT = 'EXPORT'
    LBRACKET = 'LBRACKET'
    RBRACKET = 'RBRACKET'
    AT_RATE = 'AT_RATE'
    NOT = 'NOT'
    PLUS_ASSIGN = 'PLUS_ASSIGN'
    SUB_ASSIGN = 'SUB_ASSIGN'
    MUL_ASSIGN = 'MUL_ASSIGN'
    DIV_ASSIGN = 'DIV_ASSIGN'
    MOD = 'MOD'
    NULL = 'NULL'
    DICT_STARTER = 'DICT_STARTER'
    COLON = 'COLON'
    BREAK = 'BREAK'
    BACKTICK = 'BACKTICK'
    FStringStart = 'FStringStart'
    FStringExpr = 'FStringExpr'
    FStringExprEnd = 'FStringExprEnd'
    FStringEnd = 'FStringEnd'
    CONTINUE = 'CONTINUE'


PRECEDENCE = {
    TokenType.ADD: 1,
    TokenType.SUB: 1,
    TokenType.MUL: 2,
    TokenType.DIV: 2,
    TokenType.POW: 3,
}


@dataclass
class CompilationException(Exception):
    code: int
    msg: str
    line: int
    col: int
    end_line: int
    end_col: int
    fp: str


@dataclass
class ParserError(CompilationException):
    file_content: str
    pass


@dataclass
class CompilerError(CompilationException):
    pass


@dataclass
class TokenizerError(CompilationException):
    file_content: str
    pass


KEYWORDS = {
    'func': TokenType.FUNC,
    'return': TokenType.RETURN,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'or': TokenType.OR,
    'and': TokenType.AND,
    'while': TokenType.WHILE,
    'import': TokenType.IMPORT,
    'export': TokenType.EXPORT,
    '@': TokenType.AT_RATE,
    'not': TokenType.NOT,
    'null': TokenType.NULL,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE
}


class Callable:
    pass


class IncompleteInput(Exception):
    pass


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    col: int
    end_line: int
    end_col: int


class FormatStringComponent:
    pass


@dataclass
class FormatStringStr(FormatStringComponent):
    value: str


@dataclass
class FormatStringExpr(FormatStringComponent):
    expr: str


class Tokenizer:
    class Mode(Enum):
        Normal = auto()
        FStringEpr = auto()
        FStringStr = auto()

    @dataclass
    class ModeState:
        mode: Tokenizer.Mode
        multiline: bool = False
        raw: bool = False

    def __init__(self, string: str, fp: str = '<unknown>'):
        self.string: str = string
        self.current_idx: int = 0
        self.line: int = 0
        self.col: int = 0
        self.fp: str = fp
        # self.mode: Tokenizer.TokenizerMode = self.TokenizerMode.Normal
        self.fstring_count = 0
        self.mode_stack: list[Tokenizer.ModeState] = [self.ModeState(self.Mode.Normal)]

    def is_str_prefix(self):
        i = 0
        while True:
            match self.peek(i):
                case 'm' | 'r':
                    i += 1
                case '"' | "'" | '`':
                    return True
                case _:
                    return False

    def advance(self, steps: int = 1) -> str | None:
        if steps <= 0:  # To make sure that `ch` isn't `Unbound`
            return self.get_current_char()
        for _ in range(steps):
            ch = self.get_current_char()
            if ch is None:
                return None
            self.current_idx += 1
            if ch == '\n':
                self.line += 1
                self.col = 0
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
            if ch is not None and ch.isspace() and ch != '\n':
                self.advance()
            else:
                break

    def peek(self, amnt: int = 1):
        if self.current_idx + amnt < len(self.string):
            return self.string[self.current_idx + amnt]
        else:
            return None

    def check(self, text: str) -> bool:
        end = self.current_idx + len(text)
        return self.string[self.current_idx : end] == text

    def tokenize_string(
        self,
        char: Literal["'", '"'],
        start_line,
        start_col,
        multiline: bool = False,
        raw: bool = False,
    ) -> Token:
        value = ''
        while self.get_current_char() is not None and self.get_current_char() != char:
            if not multiline and self.get_current_char() == '\n':
                break
            if self.get_current_char() == '\\' and not raw:
                self.advance()
                value += self.parse_escape_seq(char)
                # self.advance()
            else:
                value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
            self.advance()
        if self.get_current_char() != char:
            raise TokenizerError(
                1,
                'Unterminated string literal',
                start_line,
                start_col,
                self.line,
                self.col + 1,
                self.fp,
                self.string,
            )
        self.advance()
        return Token(
            TokenType.STRING, value, start_line, start_col, self.line, self.col
        )

    def tokenize_format_string(
        self, start_line, start_col, multiline: bool = False, raw: bool = False
    ) -> Token | list[Token]:
        if self.mode_stack[-1].mode == self.Mode.FStringStr:
            value = ''
            while (
                self.get_current_char() is not None and self.get_current_char() != '`'
            ):
                if (
                    self.get_current_char() == '\n'
                    and not self.mode_stack[-1].multiline
                ):
                    break
                if self.get_current_char() == '\\' and not self.mode_stack[-1].raw:
                    self.advance()
                    value += self.parse_escape_seq('`')
                    self.advance()
                elif self.check('${'):
                    self.advance(2)
                    self.mode_stack.append(self.ModeState(self.Mode.FStringEpr))
                    return [
                        Token(
                            TokenType.STRING,
                            value,
                            start_line,
                            start_col,
                            self.line,
                            self.col,
                        ),
                        Token(
                            TokenType.FStringExpr,
                            None,
                            self.line,
                            self.col,
                            self.line,
                            self.col,
                        ),
                    ]
                else:
                    value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                    self.advance()
            if self.get_current_char() != '`':
                raise TokenizerError(
                    1,
                    'Unterminated string literal',
                    start_line,
                    start_col,
                    self.line,
                    self.col + 1,
                    self.fp,
                    self.string,
                )

            self.advance()
            self.mode_stack.pop()
            if len(value) > 0:
                return [
                    Token(
                        TokenType.STRING,
                        value,
                        start_line,
                        start_col,
                        self.line,
                        self.col,
                    ),
                    Token(
                        TokenType.FStringEnd,
                        None,
                        start_line,
                        start_col,
                        self.line,
                        self.col,
                    ),
                ]
            return Token(
                TokenType.FStringEnd, None, start_line, start_col, self.line, self.col
            )

        else:
            self.mode_stack.append(self.ModeState(self.Mode.FStringStr, multiline, raw))
            self.fstring_count += 1
            return Token(
                TokenType.FStringStart,
                None,
                self.line,
                self.col - 1,
                self.line,
                self.col,
            )

    def parse_escape_seq(self, char: Literal['"', "'", '`']):
        if self.get_current_char() == '\\':
            self.advance()

        def hex_tokenize(amnt: int):
            def hex_check(c: str):
                return c[0].lower() not in '0123456789abcdef'

            self.advance()
            c = self.get_current_char()
            if c is None:
                raise TokenizerError(
                    3,
                    'Unexpected EOF when decoding escape code',
                    self.line,
                    self.col,
                    self.line,
                    self.col,
                    self.fp,
                    self.string,
                )
            if hex_check(c):
                raise TokenizerError(
                    17,
                    'Invalid hexadecimal escape code',
                    self.line,
                    self.col,
                    self.line,
                    self.col + 1,
                    self.fp,
                    self.string,
                )
            for _ in range(amnt - 1):
                self.advance()
                tmp = self.get_current_char()
                if tmp is None:
                    raise TokenizerError(
                        3,
                        'Unexpected EOF when decoding escape code',
                        self.line,
                        self.col,
                        self.line,
                        self.col + 1,
                        self.fp,
                        self.string,
                    )
                if hex_check(tmp):
                    raise TokenizerError(
                        17,
                        'Invalid hexadecimal escape code',
                        self.line,
                        self.col,
                        self.line,
                        self.col + 1,
                        self.fp,
                        self.string,
                    )
                c += tmp
            return chr(int(c, 16))

        match self.get_current_char():
            case 'n':
                return '\n'
            case 'r':
                return '\r'
            case 't':
                return '\t'
            case '\\':
                return '\\'
            case 'b':
                return '\b'
            case '\n':  # multi line strings
                return ''
            case 'f':
                return '\f'
            case 'e':
                return '\x1b'
            case 'a':
                return '\x07'
            case 'x':
                return hex_tokenize(2)
            case 'u':
                return hex_tokenize(4)
            case 'U':
                return hex_tokenize(8)
            case _:
                if self.get_current_char() == char:
                    return char
                raise TokenizerError(
                    17,
                    f'Invalid escape sequence \\{self.get_current_char()}',
                    self.line,
                    self.col,
                    self.line,
                    self.col + 1,
                    self.fp,
                    self.string,
                )

    def get_next_token(self):  # sourcery skip: extract-method, low-code-quality
        start_line = self.line
        start_col = self.col
        if self.mode_stack[-1].mode == self.Mode.FStringStr:
            return self.tokenize_format_string(start_line, start_col)
        self.skip_whitespace()
        current_char = self.get_current_char()
        if current_char is None:
            return Token(
                TokenType.EOF, None, start_line, start_col, self.line, self.col
            )  # End of input
        start_line = self.line
        start_col = self.col

        if current_char.isdigit():
            value = ''
            fl = False
            while (
                self.get_current_char() is not None
                and self.get_current_char().isdigit()  # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char() == '.'  # pyright: ignore[reportOptionalMemberAccess]
            ):
                if self.get_current_char() == '.':
                    fl = True
                value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.advance(1)
            if fl:
                return Token(
                    TokenType.FLOAT,
                    float(value),
                    start_line,
                    start_col,
                    self.line,
                    self.col,
                )
            else:
                return Token(
                    TokenType.INT,
                    int(value),
                    start_line,
                    start_col,
                    self.line,
                    self.col,
                )
        elif self.is_str_prefix():
            raw = False
            multiline = False
            while True:
                match self.get_current_char():
                    case 'm':
                        multiline = True
                    case 'r':
                        raw = True
                    case _:
                        break
                self.advance()
            char = self.get_current_char()
            self.advance()
            match char:
                case "'" | '"':
                    return self.tokenize_string(
                        char, start_line, start_col, multiline, raw
                    )
                case '`':
                    return self.tokenize_format_string(
                        start_line, start_col, multiline, raw
                    )
        elif current_char == '[':
            self.advance(1)
            return Token(
                TokenType.LBRACKET, None, start_line, start_col, self.line, self.col
            )
        elif current_char == ']':
            self.advance(1)
            return Token(
                TokenType.RBRACKET, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '@':
            self.advance(1)
            return Token(
                TokenType.AT_RATE, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '#':
            while (
                self.get_current_char() is not None and self.get_current_char() != '\n'
            ):
                self.advance()
            return self.get_next_token()
        elif self.check('+='):
            self.advance(2)
            return Token(
                TokenType.PLUS_ASSIGN, None, start_line, start_col, self.line, self.col
            )
        elif self.check('-='):
            self.advance(2)
            return Token(
                TokenType.SUB_ASSIGN, None, start_line, start_col, self.line, self.col
            )
        elif self.check('/='):
            self.advance(2)
            return Token(
                TokenType.DIV_ASSIGN, None, start_line, start_col, self.line, self.col
            )
        elif self.check('*='):
            self.advance(2)
            return Token(
                TokenType.MUL_ASSIGN, None, start_line, start_col, self.line, self.col
            )
        elif self.check('%{'):
            self.advance(2)
            return Token(
                TokenType.DICT_STARTER, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '+':
            self.advance(1)
            return Token(
                TokenType.ADD, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '.':
            self.advance(1)
            return Token(
                TokenType.DOT, None, start_line, start_col, self.line, self.col
            )
        elif self.check('true'):
            self.advance(4)
            return Token(
                TokenType.BOOL, True, start_line, start_col, self.line, self.col
            )
        elif self.check('false'):
            self.advance(5)
            return Token(
                TokenType.BOOL, False, start_line, start_col, self.line, self.col
            )
        elif self.check('=='):
            self.advance(2)
            return Token(
                TokenType.EQUAL_TO, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '=':
            self.advance(1)
            return Token(
                TokenType.ASSIGN, None, start_line, start_col, self.line, self.col
            )
        elif current_char == ':':
            self.advance(1)
            return Token(
                TokenType.COLON, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '-':
            self.advance(1)
            return Token(
                TokenType.SUB, None, start_line, start_col, self.line, self.col
            )
        elif self.check('**'):
            self.advance(2)
            return Token(
                TokenType.POW, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '*':
            self.advance(1)
            return Token(
                TokenType.MUL, None, start_line, start_col, self.line, self.col
            )
        elif self.check('!='):
            self.advance(2)
            return Token(
                TokenType.NOT_EQUAL_TO, None, start_line, start_col, self.line, self.col
            )
        elif self.check('<='):
            self.advance(2)
            return Token(
                TokenType.LTE, None, start_line, start_col, self.line, self.col
            )
        elif self.check('>='):
            self.advance(2)
            return Token(
                TokenType.GTE, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '\n':
            self.advance(1)
            return Token(
                TokenType.NEWLINE, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '(':
            self.advance(1)
            return Token(
                TokenType.LPAREN, None, start_line, start_col, self.line, self.col
            )
        elif current_char == ')':
            self.advance(1)
            return Token(
                TokenType.RPAREN, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '{':
            self.advance(1)
            return Token(
                TokenType.LBRACE, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '}':
            self.advance(1)
            if self.mode_stack[-1].mode == self.Mode.FStringEpr:
                self.mode_stack.pop()
                return Token(
                    TokenType.FStringExprEnd,
                    None,
                    start_line,
                    start_col,
                    self.line,
                    self.col,
                )

            return Token(
                TokenType.RBRACE, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '/':
            self.advance(1)
            return Token(
                TokenType.DIV, None, start_line, start_col, self.line, self.col
            )
        elif current_char == ',':
            self.advance(1)
            return Token(
                TokenType.COMMA, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '<':
            self.advance(1)
            return Token(
                TokenType.LESS_THAN, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '%':
            self.advance(1)
            return Token(
                TokenType.MOD, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '>':
            self.advance(1)
            return Token(
                TokenType.GREATER_THAN, None, start_line, start_col, self.line, self.col
            )
        elif current_char == '"':
            self.advance()
            return self.tokenize_string('"', start_line, start_col)
        elif current_char == "'":
            self.advance()
            return self.tokenize_string("'", start_line, start_col)
        elif current_char == '`':
            self.advance()
            return self.tokenize_format_string(start_line, start_col)
        elif current_char.isalpha() or current_char == '_':
            to_return = current_char
            self.advance()
            while (
                self.get_current_char() is not None
                and self.get_current_char().isalnum()  # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char() == '_'
            ):  # pyright: ignore[reportOptionalMemberAccess]
                to_return += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.advance()
            tok_type = KEYWORDS.get(to_return, TokenType.IDENTIFIER)
            return Token(
                tok_type, to_return, start_line, start_col, self.line, self.col
            )

        raise TokenizerError(
            2,
            f'Unexpected character "{current_char}"',
            self.line,
            self.col,
            self.line,
            self.col + 1,
            self.fp,
            self.string,
        )


@dataclass
class KoniType:
    display: str | None = None

    @classmethod
    def try_from(cls, s: str):
        # Iterate over all subclasses of KoniType
        for subclass in cls.__subclasses__():
            instance = subclass()  # create an instance
            if instance.display == s:
                return instance
        raise ValueError(f"No KoniType subclass with display='{s}' found")


@dataclass
class KoniStr(KoniType):
    def __init__(self):
        self.display = 'str'


@dataclass
class KoniFloat(KoniType):
    def __init__(self):
        self.display = 'float'


@dataclass
class KoniInt(KoniType):
    def __init__(self):
        self.display = 'int'


@dataclass
class KoniFunc(KoniType):
    def __init__(self):
        self.display = 'func'


@dataclass
class KoniModule(KoniType):
    def __init__(self):
        self.display = 'mod'


@dataclass
class KoniArray(KoniType):
    def __init__(self):
        self.display = 'array'


@dataclass
class KoniNull(KoniType):
    def __init__(self):
        self.display = 'null'


class BinOpType(Enum):
    ADD = TokenType.ADD
    SUB = TokenType.SUBTRACT
    OR = TokenType.OR
    AND = TokenType.AND
    LT = TokenType.LT
    LTE = TokenType.LTE
    GT = TokenType.GT
    GTE = TokenType.GTE
    MUL = TokenType.MUL
    DIV = TokenType.DIV
    POW = TokenType.POW
    EQ = TokenType.EQUAL_TO
    NEQ = TokenType.NOT_EQUAL_TO
    MOD = TokenType.MOD


class UnaryOpType(Enum):
    NEG = 'NEG'
    NOT = TokenType.NOT


@dataclass
class Warn:  # TODO: make a warning code
    message: str
    line: int
    col: int
    end_line: int
    end_col: int
    fp: str


@dataclass
class ParserWarn(Warn):  # TODO: make a warning code
    parser: Parser


@dataclass
class CompilerWarn(Warn):
    compiler: Compiler


class Parser:
    def __init__(
        self,
        tokens: list[Token],
        base_env: list[tuple],
        repl: bool = False,
        fp: str = '<unknown>',
        file_content: str = '<unknown>',
    ):
        self.base_env = base_env
        self.tokens = tokens
        self.pos = 0
        self.repl = repl
        self.fp = fp
        self.file_content: str = file_content
        self.current_token = (
            self.tokens[0] if self.tokens else Token(TokenType.EOF, None, 0, 0, 0, 0)
        )

    def incomplete_input(self):
        if self.repl:
            raise IncompleteInput

    def eat(self, token_type: TokenType):
        out = self.current_token
        if self.current_token.type != token_type:
            raise ParserError(
                3,
                f'Expected {token_type}, got {self.current_token.type}',
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                self.fp,
                self.file_content,
            )
        self.advance()
        return out

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
        else:
            self.current_token = Token(TokenType.EOF, None, 0, 0, 0, 0)

    def arithmetic_expr(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.term()
        while self.current_token and self.current_token.type in (
            TokenType.ADD,
            TokenType.SUB,
        ):
            op = self.current_token.type
            self.eat(op)
            t = yield from self.term()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                t,
            )
        return node

    def expr(self):
        node = yield from self.logical_and()
        while self.current_token.type == TokenType.OR:
            op = self.current_token.type
            self.eat(op)
            e = yield from self.logical_and()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                e,
            )

        return node

    def logical_not(self) -> Generator[ParserWarn, None, ASTNode]:
        if self.current_token.type == TokenType.NOT:
            self.eat(TokenType.NOT)
            e = yield from self.logical_not()
            return UnaryOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                UnaryOpType.NOT,
                e,
            )
        e = yield from self.equality()
        return e

    def logical_and(self):
        node = yield from self.logical_not()
        while self.current_token.type == TokenType.AND:
            op = self.current_token.type
            self.eat(op)
            e = yield from self.equality()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                e,
            )
        return node

    def comparison(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.arithmetic_expr()
        while self.current_token.type in (
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        ):
            op = self.current_token.type
            self.eat(op)
            e = yield from self.arithmetic_expr()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                e,
            )
        return node

    def equality(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.comparison()
        while self.current_token.type in (TokenType.EQUAL_TO, TokenType.NOT_EQUAL_TO):
            op = self.current_token.type
            self.eat(op)
            c = yield from self.comparison()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                c,
            )
        return node

    def term(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.power()
        while self.current_token and self.current_token.type in (
            TokenType.MUL,
            TokenType.DIV,
            TokenType.MOD,
        ):
            op = self.current_token.type
            self.eat(op)
            p = yield from self.power()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                p,
            )
        return node

    def power(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.factor()
        if self.current_token and self.current_token.type == TokenType.POW:
            op = self.current_token.type
            self.eat(TokenType.POW)
            p = yield from self.power()
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                node,
                BinOpType(op),
                p,
            )  # right-associative
        return node

    def factor(self) -> Generator[ParserWarn, None, ASTNode]:
        token = self.current_token
        if token.type == TokenType.SUB:
            self.eat(TokenType.SUB)
            f = yield from self.factor()
            return UnaryOp(
                token.line,
                token.col,
                token.end_line,
                token.end_col,
                UnaryOpType.NEG,
                f,
            )
        r = yield from self.postfix()
        return r

    def postfix(self) -> Generator[ParserWarn, None, ASTNode]:
        node = yield from self.primary()

        while self.current_token.type in (
            TokenType.DOT,
            TokenType.LPAREN,
            TokenType.LBRACKET,
        ):
            if self.current_token.type == TokenType.DOT:
                dot_line = self.current_token.line
                dot_col = self.current_token.col
                self.eat(TokenType.DOT)
                if self.current_token.type != TokenType.IDENTIFIER:
                    raise ParserError(
                        4,
                        "Expected identifier after '.'",
                        self.current_token.line,
                        self.current_token.col,
                        self.current_token.end_line,
                        self.current_token.end_col,
                        self.fp,
                        self.file_content,
                    )

                end_tok = self.eat(TokenType.IDENTIFIER)
                node = Attribute(
                    dot_line,
                    dot_col,
                    end_tok.end_line,
                    end_tok.end_col,
                    node,
                    end_tok.value,
                )

            elif self.current_token.type == TokenType.LPAREN:
                call_line = self.current_token.line
                call_col = self.current_token.col
                self.eat(TokenType.LPAREN)
                args: list[ASTNode] = []

                self.skip_newline()

                if self.current_token.type != TokenType.RPAREN:
                    e = yield from self.expr()
                    args.append(e)

                    while self.current_token.type == TokenType.COMMA:
                        self.eat(TokenType.COMMA)
                        self.skip_newline()
                        args.append((yield from self.expr()))

                self.skip_newline()

                if self.current_token.type == TokenType.EOF:
                    self.incomplete_input()

                end_tok = self.eat(TokenType.RPAREN)
                node = Call(
                    call_line, call_col, end_tok.end_line, end_tok.end_col, node, args
                )
            elif self.current_token.type == TokenType.LBRACKET:
                ln = self.current_token.line
                col = self.current_token.col
                self.eat(TokenType.LBRACKET)
                idx = yield from self.expr()
                end_tok = self.eat(TokenType.RBRACKET)
                node = GetIndex(ln, col, end_tok.end_line, end_tok.end_col, node, idx)

        return node

    def skip_newline(self):
        while self.current_token.type == TokenType.NEWLINE:
            self.eat(TokenType.NEWLINE)

    def primary(self) -> Generator[ParserWarn, None, ASTNode]:
        token = self.current_token
        if token.type == TokenType.INT:
            self.eat(TokenType.INT)
            return Number(
                token.line, token.col, token.end_line, token.end_col, token.value
            )
        elif token.type == TokenType.DICT_STARTER:
            self.eat(TokenType.DICT_STARTER)
            if self.current_token.type == TokenType.EOF:
                self.incomplete_input()
            items = []
            self.skip_newline()
            if self.current_token.type != TokenType.RBRACE:
                if self.current_token.type == TokenType.EOF:
                    self.incomplete_input()
                self.skip_newline()
                k = yield from self.expr()
                self.eat(TokenType.COLON)
                v = yield from self.expr()
                items.append((k, v))
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    if self.current_token.type == TokenType.EOF:
                        self.incomplete_input()
                    self.skip_newline()
                    k = yield from self.expr()
                    self.eat(TokenType.COLON)
                    v = yield from self.expr()
                    items.append((k, v))
            self.skip_newline()
            self.eat(TokenType.RBRACE)
            return KoniDict(
                token.line,
                token.col,
                self.current_token.line,
                self.current_token.col,
                items,
            )
        elif token.type == TokenType.LBRACKET:
            self.eat(TokenType.LBRACKET)
            if self.current_token.type == TokenType.EOF:
                self.incomplete_input()
            items = []
            self.skip_newline()
            if self.current_token.type != TokenType.RBRACKET:
                if self.current_token.type == TokenType.EOF:
                    self.incomplete_input()
                self.skip_newline()
                items.append((yield from self.expr()))
                while self.current_token.type == TokenType.COMMA:
                    self.eat(TokenType.COMMA)
                    if self.current_token.type == TokenType.EOF:
                        self.incomplete_input()
                    self.skip_newline()
                    items.append((yield from self.expr()))
                self.skip_newline()
            end_tok = self.eat(TokenType.RBRACKET)
            return Array(
                token.line, token.col, end_tok.end_line, end_tok.end_col, items
            )
        elif token.type == TokenType.FLOAT:
            self.eat(TokenType.FLOAT)
            return Float(
                token.line, token.col, token.end_line, token.end_col, token.value
            )
        elif token.type == TokenType.STRING:
            self.eat(TokenType.STRING)
            return String(
                token.line, token.col, token.end_line, token.end_col, token.value
            )
        elif token.type == TokenType.FStringStart:
            start_line = token.line
            start_col = token.col
            self.eat(TokenType.FStringStart)
            out: list[ASTNode] = []
            while True:
                if self.current_token.type == TokenType.FStringExpr:
                    self.eat(TokenType.FStringExpr)
                    t = yield from self.expr()
                    if not isinstance(t, String):
                        t = Call(
                            t.line,
                            t.col,
                            t.end_line,
                            t.end_col,
                            Variable(t.line, t.col, t.end_line, t.end_col, 'to_str'),
                            [t],
                        )

                    out.append(t)
                elif self.current_token.type == TokenType.FStringExprEnd:
                    self.eat(TokenType.FStringExprEnd)
                elif self.current_token.type == TokenType.FStringEnd:
                    self.eat(TokenType.FStringEnd)
                    break
                else:
                    t = yield from self.expr()
                    out.append(t)
            if len(out) == 1:
                yield ParserWarn(
                    'Format string with no expressions',
                    start_line,
                    start_col,
                    self.current_token.end_line,
                    self.current_token.end_col,
                    self.fp,
                    self,
                )
                return out[0]
            if len(out) == 0:
                yield ParserWarn(
                    'Empty format string',
                    token.line,
                    token.col,
                    token.end_line,
                    token.end_col,
                    self.fp,
                    self,
                )
                return String(start_line, start_col, start_line, start_col + 1, '')
            rhs = out[1]
            for node in out[2:]:
                rhs = BinOp(
                    self.current_token.line,
                    self.current_token.col,
                    self.current_token.end_line,
                    self.current_token.end_col,
                    rhs,
                    BinOpType.ADD,
                    node,
                )
            node = BinOp(
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                out[0],
                BinOpType.ADD,
                rhs,
            )
            return node

        elif token.type == TokenType.BOOL:
            self.eat(TokenType.BOOL)
            return Bool(
                token.line, token.col, token.end_line, token.end_col, token.value
            )
        elif token.type == TokenType.IDENTIFIER:
            self.eat(TokenType.IDENTIFIER)
            return Variable(
                token.line, token.col, token.end_line, token.end_col, token.value
            )
        elif token.type == TokenType.NULL:
            self.eat(TokenType.NULL)
            return Null(token.line, token.col, token.end_line, token.end_col)
        elif token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = yield from self.expr()
            if self.current_token.type == TokenType.EOF:
                self.incomplete_input()
            self.skip_newline()
            self.eat(TokenType.RPAREN)
            return node
        raise ParserError(
            3,
            f'Unexpected token {token.type}{f" `{token.value}`" if token.value is not None else ""}',
            token.line,
            token.col,
            token.end_line,
            token.end_col,
            self.fp,
            self.file_content,
        )

    def export(self) -> Generator[ParserWarn, None, ASTNode]:
        self.eat(TokenType.EXPORT)
        out = yield from self.statement()
        if out is None:
            raise ParserError(
                3,
                'Expected a statement',
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                self.fp,
                self.file_content,
            )
        if not isinstance(out, Assign):
            raise ParserError(
                5,
                'Cannot export anything other than an assignment or function',
                out.line,
                out.col,
                self.current_token.end_line,
                self.current_token.end_col,
                self.fp,
                self.file_content,
            )
        name = out.name
        ln = out.line
        col = out.col
        return Export(
            ln,
            col,
            self.current_token.end_line,
            self.current_token.end_col,
            out.value,
            name,
        )

    def is_assignable(self, e: ASTNode):
        match e:
            case GetIndex():
                return True
            case Attribute():
                return True
            case Variable():
                return True
            case _:
                return False

    def statement(self) -> Generator[ParserWarn, None, ASTNode | None]:
        self.skip_newline()
        if self.current_token.type == TokenType.RBRACE:
            return None
        elif self.current_token.type == TokenType.BREAK:
            t = self.eat(TokenType.BREAK)
            ln = t.line
            col = t.col
            return Break(ln, col, self.current_token.line, self.current_token.col)
        elif self.current_token.type == TokenType.CONTINUE:
            t = self.eat(TokenType.CONTINUE)
            return Continue(t.line, t.col, self.current_token.line, self.current_token.col)
        elif self.current_token.type == TokenType.AT_RATE:
            self.eat(TokenType.AT_RATE)
            if self.current_token.value == 'require':
                ln = self.current_token.line
                col = self.current_token.col
                self.eat(TokenType.IDENTIFIER)
                reqs = []
                req = ''

                req += self.eat(TokenType.IDENTIFIER).value

                while self.current_token.type == TokenType.DOT:
                    req += '.'
                    self.eat(TokenType.DOT)
                    req += self.eat(TokenType.IDENTIFIER).value

                reqs.append(req)
                req = ''
                while self.current_token.type == TokenType.COMMA:
                    if self.current_token.type == TokenType.EOF:
                        self.incomplete_input()
                    self.skip_newline()
                    self.eat(TokenType.COMMA)
                    req += self.eat(TokenType.IDENTIFIER).value
                    while self.current_token.type == TokenType.DOT:
                        req += '.'
                        self.eat(TokenType.DOT)
                        req += self.eat(TokenType.IDENTIFIER).value
                    reqs.append(req)
                    req = ''
                if self.current_token.type == TokenType.LBRACE:
                    blk = yield from self.block()
                    else_block: Block | None = None
                    if self.current_token.type == TokenType.ELSE:
                        self.eat(TokenType.ELSE)
                        else_block = yield from self.block()
                    return RequireStatement(
                        ln, col, blk.end_line, blk.end_col, reqs, blk, else_block
                    )
                else:
                    return BareRequire(
                        ln, col, self.current_token.line, self.current_token.col, reqs
                    )
        elif self.current_token.type == TokenType.LBRACE:
            b = yield from self.block()
            return b
        elif self.current_token.type == TokenType.FUNC:
            return (yield from self.function_decl())
        elif self.current_token.type == TokenType.IF:
            return (yield from self.if_decl())
        elif self.current_token.type == TokenType.EXPORT:
            return (yield from self.export())
        elif self.current_token.type == TokenType.WHILE:
            return (yield from self.while_decl())
        elif self.current_token.type == TokenType.IMPORT:
            ln = self.current_token.line
            col = self.current_token.col
            self.eat(TokenType.IMPORT)
            name_tok = self.eat(TokenType.IDENTIFIER)
            return Import(ln, col, name_tok.end_line, name_tok.end_col, name_tok.value)
        elif self.current_token.type == TokenType.RETURN:
            ln = self.current_token.line
            col = self.current_token.col
            self.eat(TokenType.RETURN)
            if self.current_token.type in (TokenType.NEWLINE, TokenType.RBRACE):
                return Return(
                    ln, col, self.current_token.line, self.current_token.col, None
                )
            value = yield from self.expr()
            return Return(ln, col, value.end_line, value.end_col, value)
        e = yield from self.expr()

        if self.current_token.type in (TokenType.ASSIGN, TokenType.PLUS_ASSIGN, TokenType.MUL_ASSIGN, TokenType.SUB_ASSIGN):
            t = self.current_token.type
            self.eat(t)
            value = yield from self.expr()
            if not self.is_assignable(e):
                raise ParserError(
                    18,
                    'Invalid assignment target',
                    e.line,
                    e.col,
                    value.end_line,
                    value.end_col,
                    self.fp,
                    self.file_content
                )
            match e:
                case Variable():
                    return Assign(e.line, e.col, value.end_line, value.end_col, e.name, value)
                case GetIndex():
                    return SetIndex(e.line, e.col, value.end_line, value.end_col, e.idx, value, e.item)
                case Attribute():
                    return SetAttr(e.line, e.col, value.end_line, value.end_col, e.attr, e.val, value)
            
        return e

    def if_decl(self) -> Generator[ParserWarn, None, If]:
        ln = self.current_token.line
        col = self.current_token.col
        self.eat(TokenType.IF)
        expr = yield from self.expr()
        if self.current_token.type == TokenType.EOF:
            self.incomplete_input()
        self.skip_newline()
        body = yield from self.block()
        if (
            self.current_token.type == TokenType.ELSE
            and self.peek().type == TokenType.IF
        ):
            self.eat(TokenType.ELSE)
            else_body = yield from self.if_decl()
        elif self.current_token.type == TokenType.ELSE:
            self.eat(TokenType.ELSE)
            else_body = yield from self.block()
        else:
            else_body = None
        if else_body is None:
            end_line = body.end_line
            end_col = body.end_col
        else:
            end_line = else_body.end_line
            end_col = else_body.end_col
        return If(ln, col, end_line, end_col, expr, body, else_body)

    def while_decl(self):
        ln = self.current_token.line
        col = self.current_token.col
        self.eat(TokenType.WHILE)
        expr = yield from self.expr()
        if self.current_token.type == TokenType.EOF:
            self.incomplete_input()
        self.skip_newline()
        body = yield from self.block()
        return While(ln, col, body.end_line, body.end_col, expr, body)

    def function_decl(self) -> Generator[ParserWarn, None, ASTNode]:
        ln = self.current_token.line
        col = self.current_token.col
        self.eat(TokenType.FUNC)

        name = self.eat(TokenType.IDENTIFIER).value

        self.eat(TokenType.LPAREN)
        params: list[FunctionParameter] = []
        optional = False
        if self.current_token.type == TokenType.IDENTIFIER:
            params.append(
                FunctionParameter(
                    self.current_token.line,
                    self.current_token.col,
                    self.current_token.end_line,
                    self.current_token.end_col,
                    self.eat(TokenType.IDENTIFIER).value,
                    None,
                )
            )
            if self.current_token.type == TokenType.ASSIGN:
                optional = True
                self.eat(TokenType.ASSIGN)
                params[-1].option = yield from self.primary()
                params[-1].end_col = params[-1].option.end_col
                params[-1].end_line = params[-1].option.end_line
            elif optional:
                raise ParserError(
                    7,
                    'Cannot have a non-optional argument after an optional argument',
                    self.current_token.line,
                    self.current_token.col,
                    self.current_token.end_line,
                    self.current_token.end_col,
                    self.fp,
                    self.file_content,
                )
            while self.current_token.type == TokenType.COMMA:
                self.eat(TokenType.COMMA)
                params.append(
                    FunctionParameter(
                        self.current_token.line,
                        self.current_token.col,
                        self.current_token.end_line,
                        self.current_token.end_col,
                        self.eat(TokenType.IDENTIFIER).value,
                        None,
                    )
                )
                if self.current_token.type == TokenType.ASSIGN:
                    optional = True
                    self.eat(TokenType.ASSIGN)
                    params[-1].option = yield from self.primary()
                    params[-1].end_col = self.current_token.col
                elif optional:
                    raise ParserError(
                        7,
                        'Cannot have a non-optional argument after an optional argument',
                        self.current_token.line,
                        self.current_token.col,
                        self.current_token.end_line,
                        self.current_token.end_col,
                        self.fp,
                        self.file_content,
                    )
        self.eat(TokenType.RPAREN)

        body = yield from self.block()
        return Assign(
            ln,
            col,
            body.end_line,
            body.end_col,
            name,
            Function(ln, col, body.end_line, body.end_col, params, body),
        )

    def peek(self, amnt=1):
        idx = self.pos + amnt
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(TokenType.EOF, None, 0, 0, 0, 0)

    def parse(self):
        node = yield from self.statement()
        if self.current_token.type != TokenType.EOF:
            raise ParserError(
                3,
                f'Unexpected token of type {self.current_token.type}: {self.current_token.value}',
                self.current_token.line,
                self.current_token.col,
                self.current_token.end_line,
                self.current_token.end_col,
                self.fp,
                self.file_content,
            )
        return node

    def program(self) -> Generator[ParserWarn, None, Program]:
        statements: list = []
        while self.current_token.type != TokenType.EOF:
            if self.current_token.type == TokenType.NEWLINE:
                self.eat(TokenType.NEWLINE)
                continue
            stmnt = yield from self.statement()
            if stmnt is not None:
                statements.append(stmnt)
            else:
                if self.current_token.type != TokenType.EOF:
                    self.advance()
        end_col = 0
        end_line = 0
        for i in reversed(statements):
            if i is not None:
                end_col = i.end_col
                end_line = i.end_line
                break
        return Program(0, 0, end_line, end_col, statements)

    def block(self) -> Generator[ParserWarn, None, Block]:
        self.eat(TokenType.LBRACE)
        statements = []
        line = self.current_token.line
        col = self.current_token.col
        while self.current_token.type != TokenType.RBRACE:
            self.skip_newline()
            if self.current_token.type == TokenType.EOF:
                self.incomplete_input()
                break
            stmnt = yield from self.statement()
            if stmnt is not None:
                statements.append(stmnt)
        if self.current_token.type == TokenType.EOF:
            self.incomplete_input()
        end_line = self.current_token.end_line
        end_col = self.current_token.end_col
        self.eat(TokenType.RBRACE)
        return Block(line, col, end_line, end_col, statements)


@dataclass
class BareRequire(ASTNode):
    reqs: list[str]


@dataclass
class Null(ASTNode):
    pass


@dataclass
class Break(ASTNode):
    pass
@dataclass
class Continue(ASTNode):
    pass

@dataclass
class Import(ASTNode):
    mod: str


@dataclass
class Array(ASTNode):
    items: list[ASTNode]


@dataclass
class GetIndex(ASTNode):
    item: ASTNode
    idx: ASTNode


@dataclass
class Block(ASTNode):
    statements: list[ASTNode]


@dataclass
class RequireStatement(ASTNode):
    reqs: list[str]
    statement: Block
    else_block: Block | None


@dataclass
class KoniDict(ASTNode):
    vals: list[tuple[ASTNode, ASTNode]]


@dataclass
class Number(ASTNode):
    value: int


@dataclass
class Float(ASTNode):
    value: float


@dataclass
class Bool(ASTNode):
    value: bool


@dataclass
class Call(ASTNode):
    func: ASTNode
    args: list[ASTNode]


@dataclass
class Attribute(ASTNode):
    val: ASTNode
    attr: str


@dataclass
class UnaryOp(ASTNode):
    op: UnaryOpType
    right: ASTNode


@dataclass
class BinOp(ASTNode):
    left: ASTNode
    op: BinOpType
    right: ASTNode


@dataclass
class Variable(ASTNode):
    name: str

@dataclass 
class SetIndex(ASTNode):
    idx: ASTNode
    value: ASTNode
    item: ASTNode
@dataclass
class SetAttr(ASTNode):
    attr: str
    item: ASTNode
    value: ASTNode

@dataclass
class FunctionParameter(ASTNode):
    name: str
    option: None | ASTNode


@dataclass
class Assign(ASTNode):
    name: str
    value: ASTNode


@dataclass
class String(ASTNode):
    value: str


@dataclass
class FormatString(ASTNode):
    value: list[ASTNode]


@dataclass
class Return(ASTNode):
    value: ASTNode | None


@dataclass
class Function(ASTNode):
    params: list[FunctionParameter]
    body: Block


@dataclass
class If(ASTNode):
    expr: ASTNode
    body: Block
    else_body: Block | None | If


@dataclass
class While(ASTNode):
    expr: ASTNode
    body: Block


@dataclass
class Export(ASTNode):
    lhs: ASTNode
    name: str


class NOP(ASTNode):
    pass


OP_SET_VAR = 'STORE'
OP_GET_VAR = 'RETRIEVE'
OP_PUSH_CONST = 'PUSH_CONST'
# OP_ADD = TokenType.ADD
# OP_SUB = TokenType.SUB
# OP_MUL = TokenType.MUL
# OP_DIV = TokenType.DIV
# OP_POW = TokenType.POW
# OP_GT = TokenType.GT
# OP_GTE = TokenType.GTE
# OP_LT = TokenType.LT
# OP_LTE = TokenType.LTE
# OP_EQUAL_TO = TokenType.EQUAL_TO
# OP_NOT_EQUAL_TO = TokenType.NOT_EQUAL_TO
# OP_OR = TokenType.OR
# OP_AND = TokenType.AND
# OP_CALL = 'CALL'
# NEG = 'NEG'
# OP_NEG = NEG
# OP_MOD = TokenType.MOD
# OP_NOT = TokenType.NOT


class OpcodeType(Enum):
    ADD = BinOpType.ADD
    SUB = BinOpType.SUB
    MUL = BinOpType.MUL
    DIV = BinOpType.DIV
    POW = BinOpType.POW
    LT = BinOpType.LT
    GT = BinOpType.GT
    LTE = BinOpType.LTE
    GTE = BinOpType.GTE
    EQ = BinOpType.EQ
    NEQ = BinOpType.NEQ
    OR = BinOpType.OR
    AND = BinOpType.AND
    MOD = BinOpType.MOD
    NEG = UnaryOpType.NEG
    NOT = UnaryOpType.NOT
    CALL = 'CALL'

    def __str__(self):
        v = self.value
        while isinstance(v, Enum):
            v = v.value

        return v


# OPCODE_MAP = {
#     BinOpType.ADD: OP_ADD,
#     BinOpType.SUB: OP_SUB,
#     BinOpType.MUL: OP_MUL,
#     BinOpType.DIV: OP_DIV,
#     BinOpType.POW: OP_POW,
#     BinOpType.LT: OP_LT,
#     BinOpType.GT: OP_GT,
#     BinOpType.GTE: OP_GTE,
#     BinOpType.LTE: OP_LTE,
#     BinOpType.EQ: OP_EQUAL_TO,
#     BinOpType.NEQ: OP_NOT_EQUAL_TO,
#     BinOpType.OR: OP_OR,
#     BinOpType.AND: OP_AND,
#     UnaryOpType.NEG: OP_NEG,
#     UnaryOpType.NOT: OP_NOT,
#     TokenType.MOD: OP_MOD,
# }
BUILTIN = 'BUILTIN'
NULL = 'NULL'


class Compiler:
    def __init__(
        self,
        env: list[str],
        ASTenv: list[tuple[str, Builtin]],
        attrs: list[tuple[str, int, int, tuple[tuple[str, str, str], ...] | None]],
        filepath: str,
    ):
        self.constants = []
        self.vars = []
        self.reqs: list[str] = []
        self.var_map = {}
        self.const_map = {}
        self.code = []
        self.sources: dict[str, str] = {}
        self.passed_env = env
        self.scopes: list[Compiler.Scope] = []
        self.var_count = 0
        self.ASTenv = ASTenv
        self.lines = []
        self.modules = []
        self.mod_stack: list[Compiler.Module] = [self.Module(0, 0, 0, 0, [], filepath)]
        self.filepath = filepath
        self.exports = []
        self.source_info: list[int] = []
        self.req_stack: list[
            Compiler.RequirementGroup
        ] = []  # LIFO stack for nested @require statements
        self.req_stack_not_allowed: list[
            Compiler.RequirementGroup
        ] = []  # for errors when using a feature where it isn't allowed, like the else branch of an @require statement
        self.attrs: list[
            tuple[str, int, int, tuple[tuple[str, str, str], ...] | None]
        ] = attrs
        self.break_stack: list[list[int]] = []
        self.continue_stack: list[list[int]] = []
        self.enter_scope()

    @dataclass
    class ScopeItem:
        idx: int
        value: ASTNode

    @dataclass
    class Module(ASTNode):
        exports: list[Compiler.ExportItem]
        fp: str

    @dataclass
    class ExportItem:
        name: str
        item: ASTNode

    @dataclass
    class RequirementGroup:  # I'm addicted to classes
        reqs: list[str]

    @dataclass
    class BuiltinScopeItem:
        value: Builtin

    @dataclass
    class ModuleRequest:
        name: str
        line: int
        col: int
        end_line: int
        end_col: int

    @dataclass
    class ModuleReceived:
        program: Program
        filepath: str
        content: str

    @dataclass
    class Scope:
        def __init__(self, var_map=None, args=None):
            self.var_map: dict[str, Compiler.ScopeItem] = (
                var_map if var_map is not None else {}
            )

            self.next_local = len(self.var_map)
            self.args = args if args is not None else {}

    @dataclass
    class Result:
        value: str

    def enter_scope(self, var_map=None, args=None):
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
    ) -> tuple[int, Literal['user', 'builtin'], int | None] | None:
        for depth, scope in enumerate(reversed(self.scopes)):
            if name in scope.var_map:
                return scope.var_map[name].idx, 'user', depth
        for i, item in enumerate(self.passed_env):
            if item == name:
                return i, 'builtin', None
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
        fp = self.mod_stack[-1].fp
        for i, item in enumerate(self.sources.keys()):  # TODO: make this O(1)
            if item == fp:
                self.source_info.append(i)
        return idx

    def compile(
        self,
        program: Program,
        features: Collection[Literal['source'] | Literal['line']] = [],
        input_source: str | None = None,
    ) -> Generator[CompilerWarn | ModuleRequest, ModuleReceived | None, list[str]]:
        if input_source is None and 'source' in features:
            if len(program.statements) == 0:
                end_line = 0
                end_col = 0
            else:
                end_line = program.statements[-1].end_line
                end_col = program.statements[-1].end_col
            raise CompilerError(
                8,
                'Compiler needs input source to compile with source info.',
                0,
                0,
                end_line,
                end_col,
                self.mod_stack[-1].fp,
            )
        if 'source' in features:
            self.sources[self.filepath] = (  # pyright: ignore[reportArgumentType]
                input_source
            )
        for node in program.statements:
            # empty statements (e.g. stray braces) may be None
            if node is None:
                continue
            yield from self.compile_ins(node)
            # drop any value produced by the statement so that subsequent
            # instructions start with a clean stack
            self.emit(node.line, 'POP')
        self.emit(0, 'NOP')
        output = []
        output.append('.version')
        output.append('ENV 1')
        output.append('ISA 1')
        if len(self.reqs) > 0:
            output.append('.reqs ' + ' '.join([str(x) for x in self.reqs]))

        output.append(f'.frame {self.scopes[0].next_local}')

        output.append('.const')
        for const in self.constants:
            output.append(
                f'{const[0]};{str(const[1]).replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;")};'
            )
        output.append('.code')
        for instr in self.code:
            output.append(' '.join(map(str, instr)))
        if 'line' in features:
            output.append('.line')
            for line in self.lines:
                output.append(line)
        if 'source' in features:
            output.append('.source_select')
            output += self.source_info
            for fp, source_content in self.sources.items():
                idx = len(output)
                output.append('')
                output += source_content.splitlines()
                output[idx] = f'.source {len(output)} {fp}'
        output.append('')  # to prevent errors if a source's end is the end of the file
        return output

    def raise_for_req(
        self,
        req: str,
        name: str,
        second_name: str,
        node: ASTNode,
        unsure: bool = False,
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
            ln = node.line
            col = node.col
            end_col = node.end_col
            end_line = node.end_line
            if illegal:
                if unsure:
                    yield CompilerWarn(
                        f'CRITICAL: This may need the `{req}` requirement, and is in an illegal zone. Perhaps add `@require {req}` to the top of your program?',  # TODO: warning priorities
                        ln,
                        col,
                        end_line,
                        end_col,
                        self.mod_stack[-1].fp,
                        self,
                    )
                else:
                    raise CompilerError(
                        14,
                        f'Attempted using a(n) {name} when it requires `{req}` in an illegal area',
                        ln,
                        col,
                        end_line,
                        end_col,
                        self.mod_stack[-1].fp,
                    )
            else:
                if unsure:
                    yield CompilerWarn(
                        f'This may need the `{req}` requirement. Perhaps add `@require {req}` to the top of your program?',
                        ln,
                        col,
                        end_line,
                        end_col,
                        self.mod_stack[-1].fp,
                        self,
                    )
                else:
                    self.reqs.append(req)
                    yield CompilerWarn(
                        f'{second_name} implicitly adds the `{req}` requirement. Perhaps add `@require {req}` to the top of your program to make it explicit?',
                        ln,
                        col,
                        end_line,
                        end_col,
                        self.mod_stack[-1].fp,
                        self,
                    )

    def compile_ins(
        self, node: ASTNode, *other
    ) -> Generator[CompilerWarn | ModuleRequest, ModuleReceived | None, Any]:
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
        elif isinstance(node, Null):
            idx = self.add_constant([T_NULL, ''])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, RequireStatement):
            consts: list[int] = []
            for item in node.reqs:
                consts.append(self.add_constant((2, item)))
            idx = self.emit(node.line, 'REQUIRE', *consts, None)
            self.req_stack.append(
                self.RequirementGroup(node.reqs)
            )  # create a new stack so later on warnings wont happen
            yield from self.compile_ins(node.statement)
            self.req_stack.pop()  # remove the stack after the statement
            if node.else_block is not None:
                self.req_stack_not_allowed.append(self.RequirementGroup(node.reqs))
                jmp = self.emit(node.line, 'JMP', None)
                self.code[idx] = ('REQUIRE', *consts, len(self.code))
                yield from self.compile_ins(node.else_block)
                self.req_stack_not_allowed.pop()
                self.code[jmp] = ('JMP', len(self.code))
            else:
                self.code[idx] = ('REQUIRE', *consts, len(self.code))
        elif isinstance(node, Variable):
            # if node.name in self.scopes[-1].var_map:
            idx = self.get_var(node.name)
            if idx is None:
                raise CompilerError(
                    9,
                    f'Variable {node.name} not declared',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                )
            if idx[1] == 'user':
                self.emit(node.line, OP_GET_VAR, idx[0], idx[2])  # RETRIEVE idx depth
            else:
                if node.name == '_name':
                    yield from self.raise_for_req(
                        'runtime_values', 'Runtime Value', 'Runtime Values', node
                    )
                self.emit(node.line, 'PUSH_BUILTIN', idx[0])
        elif isinstance(node, Assign) and isinstance(node.value, Function):
            res = self.get_var(node.name)
            if res is None:
                idx = self.declare_local(node.name, node.value)
                yield from self.compile_ins(node.value, node.name)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, 'DUP')
                self.emit(node.line, OP_SET_VAR, idx, 0)
                return idx, 0
            else:
                idx, cat, depth = res
                yield from self.compile_ins(node.value, node.name)

                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, 'DUP')
                if depth is None:
                    depth = 0
                self.emit(node.line, OP_SET_VAR, idx, depth)

                yield CompilerWarn(
                    f'Reassignment to a function attempted for {node.name}(). This is usually not recommended',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                    self,
                )
                return idx, 0
        elif isinstance(node, Assign):
            res = self.get_var(node.name)
            if res is None:
                yield from self.compile_ins(node.value)
                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, 'DUP')
                self.emit(node.line, OP_SET_VAR, idx, 0)
            else:
                idx, _, depth = res
                yield from self.compile_ins(node.value)
                idx = self.declare_local(node.name, node.value)
                if len(other) > 0 and other[0]:
                    self.emit(node.line, 'DUP')
                if depth is None:
                    depth = 0
                self.emit(node.line, OP_SET_VAR, idx, depth)
        elif isinstance(node, BinOp):
            yield from self.compile_ins(node.left)
            yield from self.compile_ins(node.right)
            self.emit(node.line, OpcodeType(node.op))
        elif isinstance(node, UnaryOp):
            yield from self.compile_ins(node.right)
            self.emit(node.line, OpcodeType(node.op))
        elif isinstance(node, Block):
            for statement in node.statements:
                yield from self.compile_ins(statement)
        elif isinstance(node, Bool):
            idx = self.add_constant([T_BOOL, 'true' if node.value else 'false'])
            self.emit(node.line, OP_PUSH_CONST, idx)
        elif isinstance(node, Call):
            # compile the expression that identifies the callable (variable, attribute, etc.)
            yield from self.compile_ins(node.func)
            exported = None
            # validate argument count depending on what kind of call this is
            if isinstance(node.func, Variable):
                itm = self.get_var_obj(node.func.name)[  # pyright: ignore[reportOptionalSubscript]
                    0
                ]
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
                                    f'Expected {len(req)} to {len(params)} arguments, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f'Expected exactly {len(req)} arguments, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                elif isinstance(itm, self.BuiltinScopeItem) and isinstance(
                    itm.value, BuiltinFunction
                ):
                    if itm.value.max_args is None:
                        if not (itm.value.req_args <= len(node.args)):
                            raise CompilerError(
                                11,
                                f'Expected at least {itm.value.req_args} args, got {len(node.args)}',
                                node.line,
                                node.col,
                                node.end_line,
                                node.end_col,
                                self.mod_stack[-1].fp,
                            )
                    else:
                        if not (
                            itm.value.req_args <= len(node.args) <= itm.value.max_args
                        ):
                            if itm.value.req_args == itm.value.max_args:
                                raise CompilerError(
                                    11,
                                    f'Expected exactly {itm.value.req_args} args, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f'Expected {itm.value.req_args} to {itm.value.max_args} args, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
            elif isinstance(node.func, Attribute):
                exported = None
                atr_itm: (
                    tuple[str, int, int, tuple[tuple[str, str, str], ...] | None] | None
                ) = None
                if isinstance(node.func.val, Variable):
                    obj = self.get_var_obj(node.func.val.name)
                    if obj is not None and isinstance(obj[0].value, self.Module):
                        exports = obj[0].value.exports
                        for item in exports:
                            if item.name == node.func.attr:
                                exported = item
                                break
                if exported is None:
                    for item in self.attrs:
                        if item[0] == node.func.attr:
                            atr_itm = item
                            break
                    if atr_itm is None:
                        if 'types.dicts' not in self.reqs:  # TODO
                            raise CompilerError(
                                12,
                                f'No attribute `{node.func.attr}` found',
                                node.line,
                                node.col,
                                node.end_line,
                                node.end_col,
                                self.mod_stack[-1].fp,
                            )
                else:
                    if isinstance(exported.item, Function):  # pyright: ignore[reportPossiblyUnboundVariable]
                        params = exported.item.params  # pyright: ignore[reportPossiblyUnboundVariable]
                        req: list[FunctionParameter] = []
                        for item in params:
                            if item.option is None:
                                req.append(item)
                        if not (len(req) <= len(node.args) <= len(params)):
                            if not len(req) == len(params):
                                raise CompilerError(
                                    11,
                                    f'Expected {len(req)} to {len(params)} arguments, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f'Expected exactly {len(req)} arguments, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                if atr_itm is not None and atr_itm[3] is not None:
                    for item in atr_itm[3]:
                        if len(atr_itm[3]) > 1:
                            yield from self.raise_for_req(
                                item[0], item[1], item[2], node, True
                            )
                        else:
                            yield from self.raise_for_req(
                                item[0], item[1], item[2], node, True
                            )
                elif atr_itm is not None:
                    min_args = atr_itm[1]
                    max_args = atr_itm[2]
                    if not (min_args <= len(node.args) <= max_args):
                        if min_args == max_args:
                            raise CompilerError(
                                11,
                                f'Expected exactly {min_args} args, got {len(node.args)}',
                                node.line,
                                node.col,
                                node.end_line,
                                node.end_col,
                                self.mod_stack[-1].fp,
                            )
                        else:
                            raise CompilerError(
                                11,
                                f'Expected {min_args} to {max_args} args, got {len(node.args)}',
                                node.line,
                                node.col,
                                node.end_line,
                                node.end_col,
                                self.mod_stack[-1].fp,
                            )
                elif exported is not None:
                    if isinstance(exported.item, Function):
                        min_args = 0
                        max_args = len(exported.item.params)
                        for param in exported.item.params:
                            if param.option is None:
                                min_args += 1

                        if not (min_args <= len(node.args) <= max_args):
                            if min_args == max_args:
                                raise CompilerError(
                                    11,
                                    f'Expected exactly {min_args} args, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )
                            else:
                                raise CompilerError(
                                    11,
                                    f'Expected {min_args} to {max_args} args, got {len(node.args)}',
                                    node.line,
                                    node.col,
                                    node.end_line,
                                    node.end_col,
                                    self.mod_stack[-1].fp,
                                )

                else:
                    pass

            # compile argument expressions once
            for arg in node.args:
                yield from self.compile_ins(arg)

            # emit the call instruction appropriate for the kind of callable
            if isinstance(node.func, Variable):
                itm = self.get_var_obj(node.func.name)[  # pyright: ignore[reportOptionalSubscript]
                    0
                ]
                if isinstance(itm, self.ScopeItem):
                    if isinstance(itm.value, Function):
                        params = itm.value.params
                        if len(params) > len(node.args):
                            for item in params[len(node.args) :]:
                                if item.option is not None:
                                    yield from self.compile_ins(item.option)
                        self.emit(node.line, OpcodeType.CALL, len(params))
                    else:
                        yield CompilerWarn(
                            'Could not detect how many min and max arguments for function call',
                            node.line,
                            node.col,
                            node.end_line,
                            node.end_col,
                            self.mod_stack[-1].fp,
                            self,
                        )
                        self.emit(node.line, OpcodeType.CALL, len(node.args))
                elif isinstance(itm, self.BuiltinScopeItem):
                    self.emit(node.line, OpcodeType.CALL, len(node.args))
                else:
                    raise
            
            elif isinstance(node.func, Attribute):
                if exported is not None:
                    if isinstance(exported.item, Function):
                        for item in exported.item.params[len(node.args) :]:
                            if item.option is not None:
                                yield from self.compile_ins(item.option)
                            else:
                                raise RuntimeError  # impossible
                        self.emit(node.line, OpcodeType.CALL, len(exported.item.params))
                    else:
                        raise RuntimeError  # impossible
                else:
                    self.emit(node.line, OpcodeType.CALL, len(node.args))
            else:
                pass  # falling back for future call types #TODO
        elif isinstance(node, While):
            j = len(self.code)
            yield from self.compile_ins(node.expr)
            jmp = self.emit(node.line, 'JMPIFF', None)
            self.break_stack.append([])
            self.continue_stack.append([])
            yield from self.compile_ins(node.body)
            yield from self.compile_ins(node.expr)
            self.emit(node.line, 'JMPIF', jmp + 1)
            end = len(self.code)
            self.code[jmp] = ('JMPIFF', end)
            for break_statement in self.break_stack.pop():
                self.code[break_statement] = ('JMP', end)
            for continue_statement in self.continue_stack.pop():
                input(continue_statement)
                self.code[continue_statement] = ('JMP', j-1)
        elif isinstance(node, If):
            yield from self.compile_ins(node.expr)
            jmp = self.emit(node.line, 'JMPIFF', None)
            yield from self.compile_ins(node.body)
            if node.else_body:
                jmp2 = self.emit(node.line, 'JMP', None)
                self.code[jmp] = ('JMPIFF', len(self.code))
                yield from self.compile_ins(node.else_body)
                self.code[jmp2] = ('JMP', len(self.code))
            else:
                self.code[jmp] = ('JMPIFF', len(self.code))
        elif isinstance(node, Array):
            yield from self.raise_for_req('types.arrays', 'Array', 'Arrays', node)
            for item in reversed(node.items):
                yield from self.compile_ins(item)
            self.emit(node.line, 'BUILD_ARRAY', len(node.items))
        elif isinstance(node, SetIndex):
            yield from self.raise_for_req('indexes', 'Index', 'Indexing', node)
            yield from self.compile_ins(node.item)
            yield from self.compile_ins(node.idx)
            yield from self.compile_ins(node.value)
            self.emit(node.line, 'SET_INDEX')
        elif isinstance(node, SetAttr):
            yield from self.raise_for_req('attributes', 'Attribute', 'Attributes', node)
            yield from self.compile_ins(node.item)
            yield from self.compile_ins(node.value)
            i = self.add_constant((T_STRING, node.attr))
            self.emit(node.line, 'SET_ATTR', i)
        elif isinstance(node, KoniDict):
            yield from self.raise_for_req(
                'types.dicts', 'Dictionary', 'Dictionaries', node
            )
            for item in reversed(node.vals):
                yield from self.compile_ins(item[1])
                yield from self.compile_ins(item[0])
            self.emit(node.line, 'BUILD_DICT', len(node.vals))
        elif isinstance(node, NOP):
            self.emit(0, 'NOP')
        elif isinstance(node, Function):
            jmp = self.emit(node.line, 'JMP', None)
            fn_entry = len(self.code)
            self.enter_scope({})
            for param in node.params:
                self.declare_local(param.name, param)
            yield from self.compile_ins(node.body)

            self.emit(
                node.line, 'PUSH_CONST', self.add_constant((base_env.T_NULL, None))
            )
            self.emit(node.line, 'RET')

            local_count = self.scopes[-1].next_local
            self.exit_scope()
            self.code[jmp] = ('JMP', len(self.code))
            if len(other) >= 1:
                idx = self.add_constant([T_STRING, other[0]])
                self.emit(
                    node.line,
                    'MAKE_FUNCTION',
                    fn_entry,
                    local_count,
                    len(node.params),
                    idx,
                )
            else:
                raise CompilerError(
                    13,
                    '(internal) Expected array `other` to have at least 1 value, found 0. This error should not be raised under any circumstance, please report at https://github.com/DELOLCAT/koniscript.',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                )
        elif isinstance(node, Return):
            if node.value is None:
                idx = self.add_constant((T_NULL, ''))
                self.emit(node.line, OP_PUSH_CONST, idx)
                return
            yield from self.compile_ins(node.value)
            self.emit(node.line, 'RET')
        elif isinstance(node, Export):
            yield from self.compile_ins(
                Assign(
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    node.name,
                    node.lhs,
                ),
                True,
            )
            idx = self.add_constant((T_STRING, node.name))
            self.mod_stack[-1].exports.append(self.ExportItem(node.name, node.lhs))
            self.emit(node.line, 'EXPORT', idx)
        elif isinstance(node, Attribute):
            yield from self.raise_for_req('attributes', 'Attribute', 'Attributes', node)
            broken = False
            if 'types.dicts' in self.reqs:
                yield CompilerWarn(
                    'Dictionaries are enabled, so koniscript cannot check arguments or whether this attribute exists. This will be fixed once koniscript releases a proper type checker',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                    self,
                )
            else:
                if isinstance(node.val, Variable):
                    itm = self.get_var_obj(node.val.name)
                    if itm is not None and isinstance(itm[0].value, self.Module):
                        exports = itm[0].value.exports
                        for item in exports:
                            if item.name == node.attr:
                                broken = True
                                break
                if not broken:
                    for item in self.attrs:
                        if item[0] == node.attr:
                            broken = True
                            break
                    if not broken:
                        raise CompilerError(
                            12,
                            f'Could not find attribute {node.attr}',
                            node.line,
                            node.col,
                            node.end_line,
                            node.end_col,
                            self.mod_stack[-1].fp,
                        )
            yield from self.compile_ins(node.val)
            idx = self.add_constant((T_STRING, node.attr))
            self.emit(node.line, 'GETATTR', idx)
        elif isinstance(node, GetIndex):
            yield from self.raise_for_req('indexes', 'Index', 'Indexing', node)
            yield from self.compile_ins(node.idx)
            yield from self.compile_ins(node.item)
            self.emit(node.line, 'GET_ITEM')
        elif isinstance(node, Import):
            yield from self.raise_for_req('imports', 'Import', 'Importing', node)
            self.emit(
                node.line, 'ENTER_MODULE', self.add_constant((T_STRING, node.mod))
            )
            module = yield self.ModuleRequest(
                node.mod, node.line, node.col, node.end_line, node.end_col
            )

            if module is None:
                raise TypeError('`module` is None')
            self.mod_stack.append(self.Module(0, 0, 0, 0, [], module.filepath))
            self.modules.append(node.mod)
            self.enter_scope()
            self.sources[module.filepath] = module.content
            for statement in module.program.statements:
                yield from self.compile_ins(statement)
            self.exit_scope()
            idx = self.add_constant((T_STRING, node.mod))
            self.emit(node.line, 'MAKE_MODULE', idx)
            md = self.mod_stack.pop()
            self.scopes[0].next_local += 1  # TODO: make this better
            yield from self.compile_ins(
                Assign(node.line, node.col, node.end_line, node.end_col, node.mod, md)
            )
        elif isinstance(node, self.Module):
            pass
        elif isinstance(node, Break):
            if len(self.break_stack) == 0:
                raise CompilerError(
                    15,
                    'Cannot break outside of a loop',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                )
            else:
                idx = self.emit(node.line, 'JMP', None)
                self.break_stack[-1].append(idx)
                
        elif isinstance(node, Continue):
            if len(self.continue_stack) == 0:
                raise CompilerError(
                    15,
                    'Cannot continue outside of a loop',
                    node.line,
                    node.col,
                    node.end_line,
                    node.end_col,
                    self.mod_stack[-1].fp,
                )
            else:
                idx = self.emit(node.line, 'JMP', None)
                self.continue_stack[-1].append(idx)

        else:
            raise CompilerError(
                13,
                f'Did not implement {node} yet :<',
                node.line,
                node.col,
                node.end_line,
                node.end_col,
                self.mod_stack[-1].fp,
            )
