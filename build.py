from pathlib import Path
import shutil
import subprocess
import platform
import concurrent.futures
from rich import print
import os

def run(cmd):
    print(f"[d green]Running: [b]{cmd}")
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")

def build_rust():
    run("cd ray_vm && cargo build -r")
    os.makedirs("build", exist_ok=True)
    if platform.system() == "Windows":
        if Path("build\\vm.exe").exists():
            os.remove("build\\vm.exe")
        shutil.move("ray_vm\\target\\release\\ray_vm.exe", "build\\vm.exe")
    else:
        shutil.move("ray_vm/target/release/ray_vm", "build/vm")
def build_py():
    if platform.system() == "Windows":
        run("pyinstaller win.spec")
    else:
        run("pyinstaller unix.spec")
def main():
    tasks = [build_rust, build_py]
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
