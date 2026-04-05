"""
Simple program to bench test a command.
Files are saved to ./bench/<file>, which is `.gitignore`d
"""

from time import perf_counter
from subprocess import run
from ansimarkup import ansiprint
from pathlib import Path

res = []
cmd = input('Enter the command to run (shell)\n>>> ').strip()


ansiprint('Enter the file to save to\n>>> <d>./bench/</d>', flush=True, end='')
out = Path('.') / 'bench' / input('')
out.parent.mkdir(parents=True, exist_ok=True)
for _ in range(10):
    f = perf_counter()
    run(cmd, shell=True)
    res.append(perf_counter()-f)
    print(res[-1])

avg = sum(res) / len(res)

with open(out, 'w') as f:
    f.write('\n'.join([str(i) for i in res] + [f'Avg: {avg}']))