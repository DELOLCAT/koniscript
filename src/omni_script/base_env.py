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
    ('print', BuiltinFunction('print')),
    ('sleep', BuiltinFunction('sleep')),
    ('input', BuiltinFunction('input')),
    ('to_str', BuiltinFunction('to_str')),
    ('to_int', BuiltinFunction('to_int')),
    ('to_bool', BuiltinFunction('to_bool')),
    ('to_float', BuiltinFunction('to_float')),
    ('math', BuiltinModule([BuiltinFunction('hi')], 'math')),
]
compiler_env = [x[0] for x in ASTenv]
