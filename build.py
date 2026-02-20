from pathlib import Path
import shutil
import subprocess
import platform
from rich import print
import os


def run(cmd):
    print(f'[d green]Running: [b]{cmd}')
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError(f'Command failed: {cmd}')


def build_rust():
    run('cd omni_vm && cargo build -r')
    os.makedirs('dist', exist_ok=True)
    if platform.system() == 'Windows':
        if Path('dist\\omvm.exe').exists():
            os.remove('dist\\omvm.exe')
        shutil.move('omni_vm\\target\\release\\omni_vm.exe', 'dist\\omvm.exe')
    else:
        shutil.move('omni_vm/target/release/omni_vm', 'dist/omvm')


def build_py():
    if platform.system() == 'Windows':
        run('pyinstaller win.spec')
    else:
        run('pyinstaller unix.spec')


def main():
    tasks = [build_rust, build_py]
    for task in tasks:
        try:
            print(f'[b green]Running task {task.__name__}')
            task()
        except Exception as e:
            print(f'[red b i]Build failed: {e}')
            return
    print('[green b u]Build completed! Result in dist/')


if __name__ == '__main__':
    main()
