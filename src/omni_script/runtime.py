from dataclasses import dataclass
from typing import Any


def get_with_default(lst: list | tuple, index: int, default: Any = None):
    return lst[index] if 0 <= index < len(lst) else default


@dataclass
class Builtin:
    pass


@dataclass
class BuiltinFunction(Builtin):
    name: str
    req_args: int
    max_args: int | None


class Environment:
    def __init__(self, parent=None):
        self.values = {}
        self.parent = parent

    def get(self, name):
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        raise NameError(f"Undefined variable '{name}'")

    def set(self, name, value):
        self.values[name] = value

    def assign(self, name, value):
        if name in self.values:
            self.values[name] = value
        elif self.parent:
            self.parent.assign(name, value)
        else:
            raise NameError(f"Undefined variable '{name}'")


NULL = 'NULL'
STRING = 'STRING'
FUNC = 'FUNC'
INTEGER = 'INT'
INT = INTEGER
BOOLEAN = 'BOOLEAN'
BOOL = BOOLEAN
ADD = 'ADD'
INTEGER = 'INT'
INT = INTEGER
IDENTIFIER = 'IDENTIFIER'
ASSIGN = 'ASSIGN'
NEWLINE = 'NEWLINE'
EOF = 'EOF'
DIVIDE = 'DIVIDE'
DIV = DIVIDE
MULTIPLY = 'MULTIPLY'
MUL = MULTIPLY
POWER = 'POWER'
POW = POWER
SUBTRACT = 'SUBTRACT'
SUB = SUBTRACT
RPAREN = 'RPAREN'
LPAREN = 'LPAREN'
STRING = 'STRING'
COMMA = 'COMMA'
PRECEDENCE = {ADD: 1, SUB: 1, MUL: 2, DIV: 2, POW: 3}
LBRACE = 'LBRACE'
RBRACE = 'RBRACE'
FUNC = 'FUNC'
RETURN = 'RETURN'
BOOLEAN = 'BOOLEAN'
BOOL = BOOLEAN
GREATER_THAN = 'GREATER_THEN'
GT = GREATER_THAN
LESS_THAN = 'LESS_THAN'
LT = LESS_THAN
LTE = 'LESS_THEN_OR_EQ'
BUILTIN = 'BUILTIN'
GTE = 'LESS_THEN_OR_EQ'
EQUAL_TO = 'EQUAL_TO'
NOT_EQUAL_TO = 'NOT_EQUAL_TO'
IF = 'IF'
ELSE = 'ELSE'
OR = 'OR'
AND = 'AND'
FLOAT = 'FLOAT'

VALUES = [INT, STRING, IDENTIFIER]

OPERATORS = {
    ADD: lambda a, b: a + b,
    SUB: lambda a, b: a - b,
    MUL: lambda a, b: a * b,
    DIV: lambda a, b: a / b,
    POW: lambda a, b: a**b,
    LT: lambda a, b: a < b,
    GT: lambda a, b: a > b,
    GTE: lambda a, b: a >= b,
    LTE: lambda a, b: a <= b,
    EQUAL_TO: lambda a, b: a == b,
    NOT_EQUAL_TO: lambda a, b: a != b,
    OR: lambda a, b: a or b,
    AND: lambda a, b: a and b,
}

KEYWORDS = {
    'func': FUNC,
    'return': RETURN,
    'if': IF,
    'else': ELSE,
    'or': OR,
    'and': AND,
}
TYPES = {INT: 1, STRING: 2, BOOL: 3, FUNC: 4, BUILTIN: 5, NULL: 6, FLOAT: 7}
T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6
T_FLOAT = 7


class ASTNode:
    pass


@dataclass
class Program(ASTNode):
    statements: list[ASTNode]


@dataclass
class Module(ASTNode):
    line: int
    body: Program
    name: str


@dataclass
class BuiltinModulePointer(ASTNode):
    line: int
    idx: int


@dataclass
class BuiltinModule(Builtin):
    exports: list
    name: str
