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
    await run('cd kovm && cargo build -r')
    os.makedirs('dist', exist_ok=True)
    if platform.system() == 'Windows':
        if Path('dist\\kovm.exe').exists():
            os.remove('dist\\kovm.exe')
        shutil.move('kovm\\target\\release\\kovm.exe', 'dist\\kovm.exe')
    else:
        shutil.move('kovm/target/release/kovm', 'dist/kovm')


async def build_py():
    await run('uv sync --extra nuitka')
    await run('uv run nuitka --follow-imports --mode=standalone --enable-plugin=anti-bloat --assume-yes-for-downloads src/koni_compiler/koni.py')


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
