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
    if not Path('dist/').exists():
        os.mkdir('dist/')
    if platform.system() == 'Windows':
        if Path('dist\\vm.exe').exists():
            os.remove('dist\\vm.exe')
        os.makedirs('dist', exist_ok=True)
        shutil.move('omni_vm\\target\\release\\omni_vm.exe', 'dist\\omvm.exe')
    else:
        shutil.move('omni_vm/target/release/omni_vm', 'dist/omvm')


def main():
    tasks = [build_rust]
    # Run in parallel
    for task in tasks:
        try:
            print(f'[b green]Running task {task.__name__}')
            task()
        except Exception as e:
            print(f'Build failed: {e}')
            return

    print('[green b u]Build completed! Result in dist/')
    print('[blue b]If you are developing for OmniScript, move `dist/omvm` or `dist/omvm.exe` into `src/omni_script`')

if __name__ == '__main__':
    main()
