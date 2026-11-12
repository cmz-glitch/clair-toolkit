import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_tool(*args):
    return subprocess.run(
        [sys.executable, "-m", "clair_toolkit", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def load_out(proc):
    assert proc.stdout, proc.stderr
    return json.loads(proc.stdout)
