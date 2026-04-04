"""
This script is still not fully working. If one of the steps error out, the other process doesn't stop, and is still attached to your terminal.
I'll fix it later
"""

from pathlib import Path
import shutil
import platform
from rich import print
import os
import asyncio


async def run(cmd):
    print(f'[d green]Running: [b]{cmd}')
    proc = await asyncio.create_subprocess_shell(cmd)
    code = await proc.wait()
    if code != 0:
        raise RuntimeError(f'Command failed: {cmd}')


async def build_rust():
    await run('cd omni_vm && cargo build -r')
    os.makedirs('dist', exist_ok=True)
    if platform.system() == 'Windows':
        if Path('dist\\vm.exe').exists():
            os.remove('dist\\vm.exe')
        shutil.move('omni_vm\\target\\release\\omni_vm.exe', 'dist\\omvm.exe')
    else:
        shutil.move('omni_vm/target/release/omni_vm', 'dist/omvm')


async def build_py():
    if platform.system() == 'Windows':
        await run('pyinstaller win.spec')
    else:
        await run('pyinstaller unix.spec')


async def run_task(task):
    print(f'[b green]Running task {task.__name__}')
    await task()
    print(f'[b green]Finished task {task.__name__}')


async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(run_task(build_rust))
            tg.create_task(run_task(build_py))
        print('[green b u]Build completed! Result in dist/')
    except* Exception as e:
        print('[red b]Build failed:')
        for ex in e.exceptions:
            print(f'    [red b]{e}')


if __name__ == '__main__':
    asyncio.run(main())
