from omni_script import omni
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
