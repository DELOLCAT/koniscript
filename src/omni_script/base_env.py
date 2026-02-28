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

compiler_env = ['print', 'sleep', 'input', 'to_str', 'to_int', 'to_bool']
ASTenv = [
    ('print', BuiltinFunction('print')),
    ('sleep', BuiltinFunction('sleep')),
    ('input', BuiltinFunction('input')),
    ('to_str', BuiltinFunction('to_str')),
    ('to_int', BuiltinFunction('to_int')),
    ('to_bool', BuiltinFunction('to_bool')),
    ('math', BuiltinModule([BuiltinFunction('hi')], 'math')),
]