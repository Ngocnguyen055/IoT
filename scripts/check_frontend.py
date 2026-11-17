"""Run dependency-free JavaScript behavior tests with the installed Node.js."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which("node")
    if not node:
        print("Frontend tests require Node.js. Running the web itself does not require Node.js.", file=sys.stderr)
        return 1
    tests = sorted((ROOT / "tests/frontend").glob("*.test.mjs"))
    return subprocess.run([node, "--test", *map(str, tests)], cwd=ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
