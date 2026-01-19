import main
import base_env
import ray
from pathlib import Path

def test_print():
    ray.run(Path("tests/script1.ray"))