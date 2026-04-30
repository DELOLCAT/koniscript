"""
This runs both Python and Rust tests
"""

from shutil import copy
from subprocess import run
import sys
from ansimarkup import ansiprint
from pathlib import Path


def main():    
    success = [False, False]
    
    ansiprint('<blue>Running Rust tests')
    
    proc = run(['cargo', 'test'], cwd='kovm')
    
    if proc.returncode != 0:
        ansiprint('<red><b>Failed to run Rust tests, continuing for Python tests</b></red>')
    else:
        success[0] = True
        ansiprint('<green><b>Rust tests succeeded!</b></green>')


    failed = True

    ansiprint('<blue>Building Rust VM for Python tests')
    
    proc = run(['uv', 'run', 'build_vm.py'])
    
    if proc.returncode == 0:
        if sys.platform == 'win32':
            path = Path('dist', 'kovm.exe')
        else:
            path = Path('dist', 'kovm')
        copy(path, Path('src/koni_compiler'))
        ansiprint('<blue>Running Python tests')

        proc = run(['uv', 'run', 'pytest'])

        if proc.returncode == 0:
            failed = False
    
    if failed:
        ansiprint('<red><b>Failed to run Python tests</b></red>')
    else:
        success[1] = True
        ansiprint('<green><b>Python tests succeeded!</b></green>')
    if all(success):
        ansiprint('<green><b>All tests passed!')
    elif success[0]:
        ansiprint('<yellow><b>Python tests failed, Rust succeeded')
    elif success[1]:
        ansiprint('<yellow><b>Rust tests failed, Python succeeded')
    else:
        ansiprint('<red><b>All tests failed')
