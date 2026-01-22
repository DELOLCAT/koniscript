import random
import subprocess

with open("/usr/share/dict/american-english") as f:
    wl = f.readlines()

tmp = random.randrange(len(wl))
res = []
for _ in range(100):
    res.append(wl[random.randrange(len(wl))])

subprocess.run(
    ["less"],
    input="\n".join([x.strip() for x in res]),
    text=True
)
