from omni_compiler import omni
from pathlib import Path


def test_print():
    assert (
        omni.run(Path(__file__).parent / 'test_print.om').stdout == b'Hello, world!\n'
    )


def test_recurse():
    assert (
        omni.run(Path(__file__).parent.parent / 'examples' / 'fib.om').stdout == b'55\n'
    )


def test_funcs():
    assert (
        omni.run(Path(__file__).parent / 'test_funcs.om').stdout
        == b'hihihihihi\nhihihihihi\nhihihihihihihihihihi\n'
    )


def test_string_methods():
    # make sure calling an attribute method works both as a standalone
    # expression and as a value passed into print
    assert omni.run(Path(__file__).parent / 'test_string_methods.om').stdout == b'HI\n'
