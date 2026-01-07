from main import Environment, BuiltinFunction, TYPES, NULL, STRING, FUNC, INT
from main import ADD, SUB, MUL, DIV, POW, LT, GT, GTE, LTE, EQUAL_TO, NOT_EQUAL_TO, AND, OR
import time
import main
env = Environment()
env.set('print', BuiltinFunction('print', print))
env.set('sleep', BuiltinFunction('sleep', time.sleep))
env.set('input', BuiltinFunction('input', input))


def vm_print(*args):
    py_args = [str(value) for (tag, value) in args]
    print(*py_args)
    return (TYPES[NULL], None)
def vm_sleep(arg):
    tag, value = arg
    assert tag == TYPES[INT] #TODO: make floats
    time.sleep(value)
    return (TYPES[NULL], None)
def vm_input(prompt):
    tag, value = prompt
    out = input(value)
    return (TYPES[STRING], out)
VMenv = [
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_print
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_sleep
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_input
    })
]
T_INT = 0
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6


OP_TYPES = { #TODO: implement floats
    (ADD, T_INT, T_INT): T_INT,
    (ADD, T_STRING, T_STRING): T_STRING,

    (SUB, T_INT, T_INT): T_INT,
    (MUL, T_INT, T_INT): T_INT,
    (DIV, T_INT, T_INT): T_INT,
    (POW, T_INT, T_INT): T_INT,

    (LT, T_INT, T_INT): T_BOOL,
    (GT, T_INT, T_INT): T_BOOL,
    (GTE, T_INT, T_INT): T_BOOL,
    (LTE, T_INT, T_INT): T_BOOL,

    (EQUAL_TO, T_STRING, T_STRING): T_BOOL,
    (NOT_EQUAL_TO, T_STRING, T_STRING):T_BOOL,
    (EQUAL_TO, T_INT, T_INT): T_BOOL,
    (NOT_EQUAL_TO, T_INT, T_INT): T_BOOL,

    (AND, T_BOOL, T_BOOL): T_BOOL,
    (OR,  T_BOOL, T_BOOL): T_BOOL,
}
