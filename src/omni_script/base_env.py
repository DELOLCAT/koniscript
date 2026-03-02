from omni_script.runtime import (
    BuiltinFunction,
    BuiltinModule,
)

T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6

ASTenv = [
    ("print", BuiltinFunction("print", 1, None)),
    ("sleep", BuiltinFunction("sleep", 1, 1)),
    ("input", BuiltinFunction("input", 0, 1)),
    ("to_str", BuiltinFunction("to_str", 1, 1)),
    ("to_int", BuiltinFunction("to_int", 1, 1)),
    ("to_bool", BuiltinFunction("to_bool", 1, 1)),
    ("to_float", BuiltinFunction("to_float", 1, 1)),
    ("exit", BuiltinFunction("exit", 1, 1)),
    ("math", BuiltinModule([BuiltinFunction("hi", 0, 0)],"math")),
]
compiler_env = [x[0] for x in ASTenv]
