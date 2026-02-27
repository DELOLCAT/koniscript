from pathlib import Path
import shutil
import platform
import subprocess
from rich import print
import os


def run(cmd):
    print(f'[d green]Running: [b]{cmd}')
    code = subprocess.call(cmd, shell=True)
    
    if code != 0:
        raise RuntimeError(f'Command failed: {cmd}')


def build_rust():
    run('cd omni_vm && cargo build -r')
    os.makedirs('dist', exist_ok=True)
    if platform.system() == 'Windows':
        if Path('dist\\vm.exe').exists():
            os.remove('dist\\vm.exe')
        shutil.move('omni_vm\\target\\release\\omni_vm.exe', 'dist\\omvm.exe')
    else:
        shutil.move('omni_vm/target/release/omni_vm', 'dist/omvm')


def build_py():
    if platform.system() == "Windows":
        run('pyinstaller win.spec')
    else:
        run('pyinstaller unix.spec')


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
