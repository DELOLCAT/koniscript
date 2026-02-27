from pathlib import Path
import shutil
import subprocess
import platform
from rich import print
import os
import sys

debug = False
if '-d' in sys.argv[1:] or '--debug' in sys.argv[1:]:
    debug = True
    print("[blue]Debug on")


def run(cmd):
    print(f'[d green]Running: [b]{cmd}')
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError(f'Command failed: {cmd}')


def build_rust():
    fld = "debug" if debug else "release"
    run(f'cd omni_vm && cargo build {'-r' if not debug else ''}')
    if not Path('dist/').exists():
        os.mkdir('dist/')
    if platform.system() == 'Windows':
        if Path('dist\\vm.exe').exists():
            os.remove('dist\\vm.exe')
        os.makedirs('dist', exist_ok=True)
        shutil.move(f'omni_vm\\target\\{fld}\\omni_vm.exe', 'dist\\omvm.exe')
    else:
        shutil.move(f'omni_vm/target/{fld}/omni_vm', 'dist/omvm')


def main():
    tasks = [build_rust]
    for task in tasks:
        try:
            print(f'[b green]Running task {task.__name__}')
            task()
        except Exception as e:
            print(f'Build failed: {e}')
            return

    print('[green b u]Build completed! Result in dist/')
    print(
        '[blue b]If you are developing for OmniScript, move `dist/omvm` or `dist/omvm.exe` into `src/omni_script`. Also, use `uv run build_vm.py -d`.'
    )


if __name__ == '__main__':
    main()
