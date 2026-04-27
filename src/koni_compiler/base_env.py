from koni_compiler.runtime import BuiltinFunction, BuiltinModule, Builtin, RuntimeValue
import copy
T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6

ASTenv: list[tuple[str, Builtin]] = [
    ('print', BuiltinFunction('print', 0, None)),
    ('println', BuiltinFunction('println', 0, None)),
    ('sleep', BuiltinFunction('sleep', 1, 1)),
    ('input', BuiltinFunction('input', 0, 1)),
    ('to_str', BuiltinFunction('to_str', 1, 1)),
    ('to_int', BuiltinFunction('to_int', 1, 1)),
    ('to_bool', BuiltinFunction('to_bool', 1, 1)),
    ('to_float', BuiltinFunction('to_float', 1, 1)),
    ('exit', BuiltinFunction('exit', 0, 1)),
    ('len', BuiltinFunction('len', 1, 1)),
    ('math', BuiltinModule([BuiltinFunction('hi', 0, 0)], 'math')),
    ('_name', RuntimeValue('_name'))
]
Requirement = tuple[str, str, str]  # TODO: make this more readable
attrs: list[
    tuple[str, int, int, tuple[Requirement, ...] | None]
] = [  # TODO: perhaps make this type specific somehow
    (
        'push',
        1,
        1,
        (('types.arrays', 'Array', 'Arrays'),),
    ),  # Format: name, min args, max args, possible requirement
    (
        'upper',
        0,
        0,
        (('strings.methods', 'String method', 'String methods'),),
    ),  # Properties would just be strings
    ('lower', 0, 0, (('strings.methods', 'String method', 'String methods'),)),
    ('strip', 0, 0, (('strings.methods', 'String method', 'String methods'),)),
    ('pop', 0, 0, (('types.arrays', 'Array', 'Arrays'),)),
    ('get', 1, 2, (('types.arrays', 'Array', 'Arrays'),)),
    ('contains', 1, 1, (('types.arrays', 'Array', 'Arrays'),)),
    (
        'is_empty',
        0,
        0,
        (
            ('types.arrays', 'Array', 'Arrays'),
            ('strings.methods', 'String method', 'String methods'),
        ),
    ),
    ('insert', 2, 2, (('types.arrays', 'Array', 'Arrays'),)),
    ('empty', 0, 0, (('types.arrays', 'Array', 'Arrays'),))
]

compiler_env: list[str] = [x[0] for x in ASTenv]

def make_fresh_env():
    return copy.deepcopy(ASTenv), copy.deepcopy(compiler_env), copy.deepcopy(attrs)