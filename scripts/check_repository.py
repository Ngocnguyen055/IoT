"""Check current candidate files or index contents without displaying credentials."""

import argparse
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def forbidden_path(path):
    value = path.replace("\\", "/")
    parts = value.split("/")
    name = parts[-1]
    return (bool({".venv", ".runtime", "__pycache__", "node_modules"}.intersection(parts))
            or name == "config.local.json" or name.endswith(".local.h")
            or name.endswith((".pyc", ".log", ".sqlite3", ".sqlite3-wal", ".sqlite3-shm"))
            or (name.startswith(".env") and name != ".env.example"))


def content_problems(path, content, private_values=()):
    problems = []
    if forbidden_path(path):
        problems.append(f"{path}: private/generated file must not be tracked")
    for value in private_values:
        if isinstance(value, str) and len(value) >= 8 and value in content:
            problems.append(f"{path}: contains a value from private local configuration")
            break
    if re.search(r"(?i)(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])", content):
        problems.append(f"{path}: review a literal 64-character hexadecimal value")
    return problems


def git(*arguments):
    return subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", *arguments],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout


def check_repository(staged=False):
    config = ROOT / "config.local.json"
    private_values = []
    if config.exists():
        values = json.loads(config.read_text(encoding="utf-8-sig"))
        private_values = [values.get(key) for key in ("ADMIN_PASSWORD", "DEVICE_KEY", "SESSION_SECRET")]
    arguments = ["ls-files", "-z", "--cached"]
    if not staged:
        arguments.extend(["--others", "--exclude-standard"])
    paths = sorted(set(git(*arguments).decode("utf-8").split("\0")) - {""})
    problems = []
    for path in paths:
        file = ROOT / path
        if not staged and not file.is_file():
            continue
        content = git("show", ":" + path) if staged else file.read_bytes()
        problems.extend(content_problems(path, content.decode("utf-8", errors="replace"), private_values))
    return paths, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Read index contents, not working files")
    args = parser.parse_args()
    paths, problems = check_repository(args.staged)
    if problems:
        for problem in problems:
            print("CHECK FAILED:", problem)
        return 1
    print(f"PASS: {len(paths)} candidate files; no private configuration values or forbidden paths detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
