from omni_script.runtime import BuiltinFunction, BuiltinModule, Builtin

T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6

ASTenv: list[tuple[str, Builtin]] = [
    ('print', BuiltinFunction('print', 0, None)),
    ('sleep', BuiltinFunction('sleep', 1, 1)),
    ('input', BuiltinFunction('input', 0, 1)),
    ('to_str', BuiltinFunction('to_str', 1, 1)),
    ('to_int', BuiltinFunction('to_int', 1, 1)),
    ('to_bool', BuiltinFunction('to_bool', 1, 1)),
    ('to_float', BuiltinFunction('to_float', 1, 1)),
    ('exit', BuiltinFunction('exit', 0, 1)),
    ('len', BuiltinFunction('len', 1, 1)),
    ('math', BuiltinModule([BuiltinFunction('hi', 0, 0)], 'math')),
]

attrs: list[tuple[str, int, int]] = [  # TODO: perhaps make this type specific somehow
    ('push', 1, 1),  # Format: name, min, max args
    ('upper', 0, 0),  # Properties would just be strings
    ('lower', 0, 0),
    ('strip', 0, 0),
    ('pop', 0, 0),
    ('get', 1, 2),
    ('contains', 1, 1),
    ('is_empty', 0, 0),
    ('insert', 2, 2),
    ('empty', 0, 0),
]

compiler_env: list[str] = [x[0] for x in ASTenv]
