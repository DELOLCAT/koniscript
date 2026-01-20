import shutil
import subprocess
import platform
import concurrent.futures
import os

def run(cmd):
    print(f"Running: {cmd}")
    proc = subprocess.run(cmd, shell=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}")

def build_rust():
    run("cd ray_vm && cargo build")
    if platform.system() == "Windows":
        shutil.move("ray_vm/target/release/ray_vm.exe", "dist/vm")
    else:
        shutil.move("ray_vm/target/release/ray_vm", "dist/vm")
def build_py():
    run("pyinstaller ray.spec")
    if platform.system() == "Windows":
        shutil.move("dist/ray.exe", "dist/ray.exe")
    else:
        shutil.move("dist/ray", "dist/ray")
def main():
    tasks = [build_rust, build_py]
    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(t) for t in tasks]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ Build failed: {e}")
                return

    print("✅ Build completed!")

if __name__ == "__main__":
    main()
