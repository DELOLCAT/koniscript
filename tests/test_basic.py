from koni_compiler import koni
from pathlib import Path


def test_print():
    assert (
        koni.run(Path(__file__).parent / 'test_print.kn').stdout == b'Hello, world!\n'
    )


def test_recurse():
    assert (
        koni.run(Path(__file__).parent.parent / 'examples' / 'fib.kn').stdout == b'55\n'
    )


def test_funcs():
    assert (
        koni.run(Path(__file__).parent / 'test_funcs.kn').stdout
        == b'hihihihihi\nhihihihihi\nhihihihihihihihihihi\n'
    )


def test_string_methods():
    # make sure calling an attribute method works both as a standalone
    # expression and as a value passed into print
    assert koni.run(Path(__file__).parent / 'test_string_methods.kn').stdout == b'HI\n'
