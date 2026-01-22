from typing import Any
from omni_script import base_env
class BuiltinFunction:
    def __init__(self, name, func):
        self.name = name
        self.func = func

    def __call__(self, *args) -> Any:
        return self.func(*args)
    def __repr__(self) -> str:
        return f"BuiltinFunction({self.name}, {self.func})"

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


NULL = "NULL"
STRING = "STRING"
FUNC = "FUNC"
INTEGER = "INT"
INT = INTEGER
BOOLEAN = "BOOLEAN"
BOOL = BOOLEAN
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
GREATER_THAN = "GREATER_THEN"
GT = GREATER_THAN
LESS_THAN = "LESS_THAN"
LT = LESS_THAN
LTE = "LESS_THEN_OR_EQ"
BUILTIN = "BUILTIN"
GTE = "LESS_THEN_OR_EQ"
EQUAL_TO = "EQUAL_TO"
NOT_EQUAL_TO = "NOT_EQUAL_TO"
IF = "IF"
ELSE = "ELSE"
OR = "OR"
AND = "AND"
FLOAT = "FLOAT"

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
    "and":AND
}
TYPES = {
    INT: 1,
    STRING: 2,
    BOOL: 3,
    FUNC: 4,
    BUILTIN: 5,
    NULL: 6,
    FLOAT:7
}
T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6
T_FLOAT = 7
class ASTNode:
    pass

def to_type(value:tuple[int, Any]) -> Any:
    tag, val = value
    match tag:
        case 1:
            return int(base_env.vm_to_int(value)[1])
        case 2:
            return str(base_env.vm_to_str(value)[1])
        case 3:
            return bool(base_env.vm_to_bool(value)[1])
        case 4:
            raise NotImplementedError
        case 5:
            raise DeprecationWarning
        case 6:
            return None
class Program(ASTNode):
    def __init__(self, statements):
        self.statements: list[ASTNode] = statements

    def __repr__(self) -> str:
        return f"Program({self.statements})"

class Module(ASTNode):
    def __init__(self, line:int, body: Program, name:str):
        self.line = line
        self.body = body
        self.name = name
    def __repr__(self):
        return f"Module({self.body})"
class BuiltinModulePointer(ASTNode):
    def __init__(self, line:int, idx:int):
        self.line = line
        self.idx = idx
    def __repr__(self):
        return f"BuiltinModulePointer({self.line}, {self.idx})"
class BuiltinModule():
    def __init__(self, exports: list, name:str):
        self.exports = exports
        self.name = name
    def __repr__(self):
        return f"BuiltinModule({self.exports}, {self.name})"