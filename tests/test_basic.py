import main
import base_env
import omni_script
from pathlib import Path

def test_print():
    omni_script.run(Path("tests/script1.om"))