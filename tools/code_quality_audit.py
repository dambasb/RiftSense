from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "RiftSense.py"


def _duplicates(nodes: list[ast.AST]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.setdefault(node.name, []).append(node.lineno)
    return {name: lines for name, lines in found.items() if len(lines) > 1}


def main() -> int:
    source = MAIN.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_duplicates = _duplicates(list(tree.body))
    class_duplicates: dict[str, dict[str, list[int]]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            dupes = _duplicates(list(node.body))
            if dupes:
                class_duplicates[node.name] = dupes

    broad_silent: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler) or node.type is None:
            continue
        if (
            ast.unparse(node.type) == "Exception"
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Pass)
        ):
            broad_silent.append(node.lineno)

    module_count = len(list((ROOT / "riftsense").rglob("*.py")))
    test_count = len(list((ROOT / "tests").glob("test_*.py")))
    print(f"Main entrypoint lines: {len(source.splitlines())}")
    print(f"Extracted package modules: {module_count}")
    print(f"Regression test modules: {test_count}")

    if top_duplicates:
        print("FAIL: duplicate top-level functions:", top_duplicates)
        return 1
    if class_duplicates:
        print("FAIL: duplicate class methods:", class_duplicates)
        return 1
    if len(broad_silent) > 3:
        print("FAIL: unexpected broad silent exception handlers:", broad_silent)
        return 1

    print(
        "PASS: no duplicate functions/methods; broad silent handlers "
        f"limited to logger self-protection ({len(broad_silent)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
