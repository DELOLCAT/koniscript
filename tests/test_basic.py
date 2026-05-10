import pytest

from koni_compiler import koni
from pathlib import Path


TESTS = Path(__file__).parent


def test_print():
    assert koni.run(TESTS / 'test_print.kn').stdout == b'Hello, world!\n'


def test_recurse():
    assert koni.run(TESTS.parent / 'examples' / 'fib.kn').stdout == b'55\n'


def test_funcs():
    assert (
        koni.run(TESTS / 'test_funcs.kn').stdout
        == b'hihihihihi\nhihihihihi\nhihihihihihihihihihi\n'
    )


def test_string_methods():
    assert koni.run(TESTS / 'test_string_methods.kn').stdout == b'HI\n'


def test_arithmetic():
    out = koni.run(TESTS / 'test_arithmetic.kn').stdout
    assert out == b'5\n6\n12\n5\n8\n1\n14\n20\n'


def test_variables():
    out = koni.run(TESTS / 'test_variables.kn').stdout
    assert out == b'5\nhello\n10\n5\n'


def test_comparison():
    out = koni.run(TESTS / 'test_comparison.kn').stdout
    assert out == b'true\ntrue\ntrue\ntrue\ntrue\ntrue\nfalse\nfalse\nfalse\nfalse\n'


def test_logical():
    out = koni.run(TESTS / 'test_logical.kn').stdout
    assert out == b'true\nfalse\ntrue\nfalse\nfalse\ntrue\ntrue\n'


def test_if_else():
    out = koni.run(TESTS / 'test_if_else.kn').stdout
    assert out == b'equal\nmedium\n'


def test_while():
    out = koni.run(TESTS / 'test_while.kn').stdout
    assert out == b'0\n1\n2\n3\n4\n0\n1\n2\n'


def test_break():
    out = koni.run(TESTS / 'test_break.kn').stdout
    assert out == b'0\n1\n2\n'


def test_arrays():
    out = koni.run(TESTS / 'test_arrays.kn').stdout
    assert out == b'1\n2\nhello\nfirst\nsecond\n'


def test_compound_assign():
    out = koni.run(TESTS / 'test_compound_assign.kn').stdout
    assert out == b'8\n6\n6\n3\n'


def test_type_conversion():
    out = koni.run(TESTS / 'test_type_conv.kn').stdout
    assert out == b'42\n42\n3.14\ntrue\nfalse\n'


def test_len():
    out = koni.run(TESTS / 'test_len.kn').stdout
    assert out == b'5\n0\n3\n0\n'


def test_unary_negation():
    out = koni.run(TESTS / 'test_unary.kn').stdout
    assert out == b'-5\n1\n-5\n'


def test_floats():
    out = koni.run(TESTS / 'test_floats.kn').stdout
    assert out == b'3.14\n4\n2.5\n'


def test_null():
    out = koni.run(TESTS / 'test_null.kn').stdout
    assert out == b'null\n'


def test_first_class_functions():
    out = koni.run(TESTS / 'test_first_class_funcs.kn').stdout
    assert out == b'Running...\ncallback called\n'


def test_import():
    out = koni.run(TESTS / 'test_import.kn').stdout
    assert out == b'Hello World\n42\n'

def test_closures():
    out = koni.run(TESTS / 'test_closures.kn').stdout
    assert out == b'2\n4\n4\n8\n12\n'
    
def test_arr_dict_assign():
    out = koni.run(TESTS / 'test_arr_dict_assign.kn').stdout
    assert out == b'baz\nbar\n--\nfoo\nboo\nbaz\n'
    
def test_decl_error():
    with pytest.raises(SystemExit):
        out = koni.run(TESTS / 'test_decl_error.kn')
        assert out.returncode != 0
