from pathlib import Path
import shutil
import platform
import subprocess
from rich import print
import os
import sys

if '-r' in sys.argv:
    debug = False
else:
    debug = True
    print('[b]Debug mode')


def run(cmd):
    print(f'[d green]Running: [b]{cmd}')
    code = subprocess.call(cmd, shell=True)

    if code != 0:
        raise RuntimeError(f'Command failed: {cmd}')


def build_rust():
    run(f'cd kovm && cargo build{" -r" if not debug else ""}')
    os.makedirs('dist', exist_ok=True)
    if platform.system() == 'Windows':
        if Path('dist\\vm.exe').exists():
            os.remove('dist\\vm.exe')
        shutil.move(
            f'kovm\\target\\{"debug" if debug else "release"}\\kovm.exe',
            'dist\\omvm.exe',
        )
    else:
        shutil.move(
            f'kovm/target/{"debug" if debug else "release"}/kovm', 'dist/omvm'
        )


def run_task(task):
    print(f'[b green]Running task {task.__name__}')
    task()
    print(f'[b green]Finished task {task.__name__}')


def main():
    try:
        build_rust()
        print('[green b u]Build completed! Result in dist/')
    except* Exception as e:
        print('[red b]Build failed:')
        for ex in e.exceptions:
            print(f'    [red b]{e}')


if __name__ == '__main__':
    main()
