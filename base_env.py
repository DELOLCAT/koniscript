from runtime import Environment, BuiltinFunction, NULL, STRING, FUNC, INT, BOOL, TYPES
from runtime import ADD, SUB, MUL, DIV, POW, LT, GT, GTE, LTE, EQUAL_TO, NOT_EQUAL_TO, AND, OR
import time
from typing import Any
T_INT = 1
T_STRING = 2
T_BOOL = 3
T_FUNC = 4
T_BUILTIN = 5
T_NULL = 6

def vm_print(*args):
    py_args = [vm_to_str(value) for value in args]
    py_args = [value for tag, value in args]
    print(*py_args)
    return (TYPES[NULL], None)
def vm_sleep(arg):
    time.sleep(vm_to_int(arg)[1])
    return (TYPES[NULL], None)
def vm_input(prompt: tuple[int, Any]) -> tuple[int, str]:
    tag, value = prompt
    tag = int(tag)
    out = input(vm_to_str(prompt)[1])
    return (TYPES[STRING], out)
def vm_to_str(input: tuple[int, Any]) -> tuple[int, str]:
    tag, value = input
    tag = int(tag)
    if tag == TYPES[INT]:
        return (TYPES[STRING], str(value))
    elif tag == TYPES[BOOL]:
        return (TYPES[STRING], str(value))
    elif tag == TYPES[STRING]:
        return input
    else:
        raise RuntimeError(f"{tag}:{value} cannot be converted to a string")
def vm_to_int(input:tuple[int, Any]) -> tuple[int, int]:
    tag, value = input
    tag = int(tag)
    if tag == TYPES[STRING]:
        return (TYPES[INT], int(value))
    elif tag == TYPES[BOOL]:
        return (TYPES[INT], int(1 if value else 0))
    elif tag == TYPES[INT]:
        return (int(tag), int(value))
    else:
        raise RuntimeError(f"{tag}:{value} cannot be converted to an integer") #TODO: make this better
def vm_to_bool(value: tuple[int, Any]) -> tuple[int, bool]:
    tag, val = value
    tag = int(tag)

    if tag == T_INT:
        return (T_BOOL, val != 0)

    if tag == T_BOOL:
        if str(val).strip().isdigit():
            return (T_BOOL, str(val).strip() != 0)
        if str(val).lower() == "true":
            return (T_BOOL, True)
        return (T_BOOL, False)

    if tag == T_STRING:
        s = val.strip().lower()
        if s == "true":
            return (T_BOOL, True)
        if s == "false":
            return (T_BOOL, False)
        raise RuntimeError(f"Cannot convert string '{val}' to bool")

    raise RuntimeError(f"{tag}:{val} cannot be converted to bool")
        
env = Environment()
env.set('print', BuiltinFunction('print', print))
env.set('sleep', BuiltinFunction('sleep', time.sleep))
env.set('input', BuiltinFunction('input', input))
env.set('to_str', BuiltinFunction('input', vm_to_str))
env.set('to_int', BuiltinFunction('input', vm_to_int))




VMenv = [
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_print,
        "name":"print"
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_sleep,
        "name":"sleep"
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_input,
        "name":"input"
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_to_str,
        "name":"to_str"
    }),
    (TYPES[FUNC], {
        "type":"builtin",
        "func":vm_to_int,
        "name":"to_int"
    })
]
compiler_env=[i[1]["name"] for i in VMenv]
ASTenv  = [
    ('print', BuiltinFunction('print', vm_print)),
    ('sleep', BuiltinFunction('sleep', vm_sleep)),
    ('input', BuiltinFunction('input', vm_input)),
    ('to_str', BuiltinFunction('to_str', vm_to_str)),
    ('to_int', BuiltinFunction('to_int', vm_to_int))
]


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
