#!/usr/bin/env python3
"""Run the release gates used before a RiftSense source push."""

from __future__ import annotations

from pathlib import Path
import os
import py_compile
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def run(label: str, command: list[str]) -> None:
    print()
    print(f"== {label} ==")
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode:
        raise SystemExit(result.returncode)


# Audit pristine source before anything can create caches.
run("Public source audit", [sys.executable, str(TOOLS / "pre_push_public_audit.py")])
run("Regression tests", [sys.executable, str(TOOLS / "run_tests.py")])
run("Code quality audit", [sys.executable, str(TOOLS / "code_quality_audit.py")])

# Compile every Python source into a temporary directory so the public tree stays clean.
with tempfile.TemporaryDirectory(prefix="riftsense-compile-") as temp_dir:
    temp = Path(temp_dir)
    for index, source in enumerate(sorted(ROOT.rglob("*.py"))):
        if "__pycache__" in source.parts:
            continue
        py_compile.compile(
            str(source),
            cfile=str(temp / f"source-{index}.pyc"),
            doraise=True,
        )

print()
print("Python compile: PASS")

# Requires current Riot Data Dragon access.
run("Current Summoner's Rift item audit", [sys.executable, str(TOOLS / "pre_push_audit.py")])

print()
print("LOCAL RELEASE CHECKS: PASS")
print("Final live-machine gate: Settings > Riot & Sync > Verify & Sync")
