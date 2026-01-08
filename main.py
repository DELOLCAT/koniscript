from typing import Any
import base_env
# from rich import print
from runtime import BuiltinFunction, TYPES, Environment
from warnings import warn
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
GTE = "LESS_THEN_OR_EQ"
EQUAL_TO = "EQUAL_TO"
NOT_EQUAL_TO = "NOT_EQUAL_TO"
IF = "IF"
ELSE = "ELSE"
OR = "OR"
AND = "AND"

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



class Callable:
    pass


class IncompleteInput(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value




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
    def check(self, text: str) -> bool:
        end = self.current_idx + len(text)
        return self.string[self.current_idx:end] == text
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
        elif current_char == "#":
            while not self.get_current_char() == "\n":
                self.current_idx+=1
            return self.get_next_token()
        elif current_char == "+":
            self.current_idx += 1
            # self.current_token
            return Token(ADD, None)
        elif self.check("true"):
            self.current_idx += 4
            return Token(BOOL, True)
        elif self.check("false"):
            self.current_idx += 5
            return Token(BOOL, False)
        elif self.check("=="):
            self.current_idx += 2
            return Token(EQUAL_TO, None)
        elif current_char == "=":
            self.current_idx += 1
            return Token(ASSIGN, None)
        elif current_char == "-":
            self.current_idx += 1
            return Token(SUB, None)
        elif self.check("**"):
            self.current_idx += 2
            return Token(POW, None)
        elif current_char == "*":
            self.current_idx += 1
            return Token(MUL, None)
        elif self.check ("!="):
            self.current_idx += 2
            return Token(NOT_EQUAL_TO, None)
        elif self.check("<="):
            self.current_idx += 2
            return Token(LTE, None)
        elif self.check(">="):
            self.current_idx += 2
            return Token(GTE, None)
        elif current_char == "\n":
            self.current_idx += 1
            return Token(NEWLINE, None)
        elif current_char == "(":
            self.current_idx += 1
            return Token(LPAREN, None)
        elif current_char == ")":
            self.current_idx += 1
            return Token(RPAREN, None)
        elif current_char == "{":
            self.current_idx += 1
            return Token(LBRACE, None)
        elif current_char == "}":
            self.current_idx += 1
            return Token(RBRACE, None)
        elif current_char == "/":
            self.current_idx += 1
            return Token(DIV, None)
        elif current_char == ",":
            self.current_idx += 1
            return Token(COMMA, None)
        elif current_char == "<":
            self.current_idx += 1
            return Token(LESS_THAN, None)
        elif current_char == ">":
            self.current_idx += 1
            return Token(GREATER_THAN, None)
        elif current_char == '"':
            self.current_idx += 1
            value = ""
            while (
                self.get_current_char() is not None and self.get_current_char() != '"'
            ):

                if self.get_current_char() == "\\":
                    self.current_idx+=1
                    match self.get_current_char():
                        case "n":
                            value += "\n"
                        case "t":
                            value += "\t"
                        case _: 
                            value += self.get_current_char() # pyright: ignore[reportOperatorIssue]
                else:
                    value += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            if self.get_current_char() != '"':
                raise SyntaxError("Unterminated string literal")
            self.current_idx += 1
            return Token(STRING, value)

        elif current_char.isalpha() or current_char == "_":
            to_return = current_char
            self.current_idx += 1
            while (
                self.get_current_char() is not None
                and self.get_current_char().isalnum()  # pyright: ignore[reportOptionalMemberAccess]
                or self.get_current_char() == "_"
            ):  # pyright: ignore[reportOptionalMemberAccess]
                to_return += self.get_current_char()  # pyright: ignore[reportOperatorIssue]
                self.current_idx += 1
            tok_type = KEYWORDS.get(to_return, IDENTIFIER)
            return Token(tok_type, to_return)

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

    def arithmetic_expr(self):
        node = self.term()
        while self.current_token and self.current_token.type in (ADD, SUB):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.term())
        return node
    def expr(self):
        node = self.logical_and()
        while self.current_token.type == OR:
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.logical_and())
        
        return node
    def logical_and(self):
        node = self.equality()
        while self.current_token.type == AND:
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.equality())
        return node
    def comparision(self):
        node = self.arithmetic_expr()
        while self.current_token.type in (LT, GT, LTE, GTE):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.arithmetic_expr())
        return node
    
    def equality(self):
        node = self.comparision()
        while self.current_token.type in (EQUAL_TO, NOT_EQUAL_TO):
            op = self.current_token.type
            self.eat(op)
            node = BinOp(node, op, self.comparision())
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
        elif token.type == BOOL:
            self.eat(BOOL)
            return Bool(token.value)
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
        while self.current_token.type == NEWLINE:
            self.eat(NEWLINE)

        if self.current_token.type == RBRACE:
            return None
        if self.current_token.type == LBRACE:
            return self.block()
        if self.current_token.type == FUNC:
            return self.function_decl()
        if self.current_token.type == IF:
            return self.if_decl()
        elif self.current_token.type == RETURN:
            self.eat(RETURN)
            if self.current_token.type in (NEWLINE, RBRACE):
                return Return(None)
            value = self.expr()
            return Return(value)
        elif self.current_token.type == IDENTIFIER:
            next_tok = self.peek()
            if next_tok and next_tok.type == ASSIGN:
                name = self.current_token.value
                self.eat(IDENTIFIER)
                self.eat(ASSIGN)
                value = self.expr()
                return Assign(name, value)
        return self.expr()
    def if_decl(self):
        self.eat(IF)
        if self.current_token.type == EOF:
            raise IncompleteInput
        self.eat(LPAREN)
        expr = self.expr()
        if self.current_token.type == EOF:
            raise IncompleteInput
        self.eat(RPAREN)
        body = self.block()
        if self.current_token.type == ELSE and self.peek().type == IF:
            self.eat(ELSE)
            else_body = self.if_decl()
        elif self.current_token.type == ELSE:
            self.eat(ELSE)
            else_body = self.block()
        else:
            else_body = None
        return If(expr, body, else_body)
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
        return Assign(name, Function(params, body))

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
        return Block(statements)


class ASTNode:
    pass


class Block(ASTNode):
    def __init__(self, statements:list[ASTNode]):
        self.statements = statements
    def __repr__(self):
        return f"Block({self.statements})"


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

class Bool(ASTNode):
    def __init__(self, value:bool):
        self.value = value
    def __repr__(self) -> str:
        return f"Bool({self.value})"

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




class UserFunction(Call):
    def __init__(self, params, body, closure):
        self.params = params
        self.body = body
        self.closure = closure

    def __repr__(self):
        return f"UserFunction({self.params}, {self.body}, {self.closure})"


class String(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"String({self.value})"


class Return(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Return({self.value})"


class Function(ASTNode):
    def __init__(self, params, body):
        self.params = params
        self.body = body

    def __repr__(self):
        return f"Function({self.params}, {self.body})"

class If(ASTNode): #TODO: Implement else if and multiple elses
    def __init__(self, expr:ASTNode, body:Block, else_body:Block | None):
        self.expr = expr
        self.body = body
        self.else_body = else_body
    def __repr__(self):
        return f"If({self.expr}, {self.body}, {self.else_body})"
class NOP(ASTNode):
    pass
def eval_ast(node: ASTNode, env: Environment):
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
    AND: OP_AND
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
        self.enter_scope()
        
        #for item in env:
        #    self.declare_local(item)


    def enter_scope(self, var_map={}, args={}):
        self.scopes.append(Scope(var_map, args))
    def exit_scope(self):
        self.scopes.pop()
    def add_constant(self, value:tuple | list):
        value_tuple = tuple(value)
        if value_tuple in self.const_map:
            return self.const_map[value_tuple]
        index = len(self.constants)
        self.constants.append(value_tuple)
        self.const_map[value_tuple] = index
        return index
    #def set_var(self, name):
    #    if name in self.var_map:
    #        index = self.var_map[name]
    #        return index
    #    index = len(self.var_map)
    #    self.var_map[name] = index
    #    return index
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
    #def get_var(self, name):
    #    if name not in self.var_map:
    #        raise RuntimeError(f"Variable {name} not declared")
    #    return self.var_map[name]
    def emit(self, opcode, *operands):
        idx = len(self.code)
        self.code.append((opcode, *operands))
        return idx
    def compile(self, program:Program):
        for node in program.statements:
            self.compile_ins(node)
        self.emit("NOP")
        output = []
        output.append(".const")
        for const in self.constants:
            output.append(f'{const[0]}"{str(const[1]).replace("\n", "\\n").replace(r"\\", r"\\")}"')
        output.append(".code")
        for instr in self.code:
            output.append(" ".join(map(str, instr)))
        return output
    def compile_ins(self, node:ASTNode):
        if isinstance(node, String):
            idx = self.add_constant([TYPES[STRING], node.value])
            self.emit(OP_PUSH_CONST, idx)
        elif isinstance(node, Number):
            idx = self.add_constant([TYPES[INT], node.value])
            self.emit(OP_PUSH_CONST, idx)
        elif isinstance(node, Variable):
            #if node.name in self.scopes[-1].var_map:
                idx = self.get_var(node.name)
                if idx is None:
                    raise RuntimeError(f"Variable {node.name} not declared")
                if idx[1] == 'user':
                    self.emit(OP_GET_VAR, idx[0], idx[2])
                else:
                    self.emit("PUSH_BUILTIN", idx[0])
            #else:
            #    found = False
            #    for i, item in enumerate(self.passed_env):
            #        if item == node.name:
            #            found = True
            #            self.emit("PUSH_BUILTIN", i)
            #            break
            #    if not found:
            #        raise RuntimeError(f"Could not find var {node.name}")
        elif isinstance(node, Assign) and isinstance(node.value, Function):
            res = self.get_var(node.name)
            if res is None:
                idx = self.declare_local(node.name)
                self.compile_ins(node.value)
                self.emit(OP_SET_VAR, idx, 0)
            else:
                idx, cat, depth = res
                if cat == "builtin":
                    raise RuntimeError("Attempted to assign a value to a builtin")
                self.compile_ins(node.value)
                idx = self.declare_local(node.name)
                self.emit(OP_SET_VAR, idx, depth)
                warn(f"Reassignment to a function attempted for {node.name}. This is usually not reccomended.") #TODO: somehow get the line number
        elif isinstance(node, Assign):
            res = self.get_var(node.name)
            if res is None:
                self.compile_ins(node.value)
                idx = self.declare_local(node.name)
                self.emit(OP_SET_VAR, idx, 0)
            else:
                idx, cat, depth = res
                if cat == "builtin":
                    raise RuntimeError("Attempted to assign a value to a builtin")
                self.compile_ins(node.value)
                idx = self.declare_local(node.name)
                self.emit(OP_SET_VAR, idx, depth)
        elif isinstance(node, BinOp):
            self.compile_ins(node.left)
            self.compile_ins(node.right)
            self.emit(OPCODE_MAP[node.op])
        elif isinstance(node, Block):
            for statement in node.statements:
                self.compile_ins(statement)
        elif isinstance(node, Bool):
            idx = self.add_constant([TYPES[BOOL], "true" if node.value else "false"])
            self.emit(OP_PUSH_CONST, idx)
        elif isinstance(node, Call):
            self.compile_ins(node.func)
            for arg in node.args:
                self.compile_ins(arg)
            self.emit(OP_CALL, len(node.args))
        elif isinstance(node, If):
            self.compile_ins(node.expr)
            jmp = self.emit("JMPIFF", None)
            self.compile_ins(node.body)
            if node.else_body:
                jmp2 = self.emit("JMP", None)
                self.code[jmp] = ("JMPIFF", len(self.code))
                self.compile_ins(node.else_body)
                self.code[jmp2] = ("JMP",len(self.code))
            else:
                self.code[jmp] = ("JMPIFF", len(self.code))

        elif isinstance(node, NOP):
            self.emit("NOP")
        elif isinstance(node, Function):
            jmp  = self.emit("JMP", None)
            fn_entry = len(self.code)
            self.enter_scope({})

            for param in node.params:
                self.declare_local(param)
            self.compile_ins(node.body)

            self.emit("PUSH_CONST", self.add_constant((base_env.T_NULL, None)))
            self.emit("RET")

            local_count = self.scopes[-1].next_local
            self.exit_scope()
            self.code[jmp] = ("JMP", len(self.code))
            self.emit("MAKE_FUNCTION", fn_entry, local_count, len(node.params))
        elif isinstance(node, Return):
            assert len(self.scopes) > 1
            self.compile_ins(node.value)
            self.emit("RET")
        else:
            raise NotImplementedError(f"Did not implement {node} yet :<")



def main():
    tkns = [Token(IDENTIFIER, "print"), Token(LPAREN, None), Token(STRING, "hi"), Token(RPAREN, None), Token(EOF, None)]
    psr = Parser(tkns)
    program = psr.program()
    import base_env
    env = base_env.ASTenv
    compiler = Compiler(env, base_env.ASTenv)
    print(compiler.compile(program))
    
if __name__ == "__main__":
    main()
