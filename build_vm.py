from pathlib import Path
import shutil
import subprocess
import platform
from rich import print
import os

def run(cmd):
    print(f"[d green]Running: [b]{cmd}")
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")

def build_rust():
    run("cd omni_vm && cargo build -r")
    if platform.system() == "Windows":
        if Path("dist\\vm.exe").exists():
            os.remove("dist\\vm.exe")
        os.makedirs("dist", exist_ok=True)
        shutil.move("omni_vm\\target\\release\\omni_vm.exe", "dist\\omni_vm.exe")
    else:
        shutil.move("omni_vm/target/release/omni_vm", "dist/omni_vm")
def main():
    tasks = [build_rust]
    # Run in parallel
    for task in tasks:
        try:
            print(f"[b green]Running task {task.__name__}")
            task()
        except Exception as e:
            print(f"❌ Build failed: {e}")
            return

    print("[green b u]✅ Build completed! Result in dist/")

if __name__ == "__main__":
    main()
