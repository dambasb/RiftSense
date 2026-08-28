#!/usr/bin/env python3
"""Audit the RiftSense public source tree for secrets and local runtime data."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "RiftSense.py",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "CHANGELOG.md",
    ".gitignore",
    "profiles.json",
    "traits.json",
    "draft_profiles.json",
    "rune_profiles.json",
    "assets/riftsense_logo.png",
    "assets/riftsense_icon.png",
)

FORBIDDEN_ROOT_ENTRIES = {
    ".pytest_cache",
    ".mypy_cache",
    "history",
    "cache",
    "logs",
    "ai_reviews",
    "settings.json",
    "player_memory.json",
    "performance_history.json",
    "rank_progress.json",
    "riot_account.json",
}

FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".log",
    ".zip",
    ".exe",
    ".msi",
}

SECRET_PATTERNS = (
    (
        "Riot API key",
        re.compile(
            r"RGAPI-[A-Za-z0-9_-]{20,}",
            re.IGNORECASE,
        ),
    ),
    (
        "OpenAI-style API key",
        re.compile(
            r"sk-[A-Za-z0-9_-]{20,}",
        ),
    ),
    (
        "literal Windows user path",
        re.compile(
            r"[A-Za-z]:\\Users\\[^\\\r\n\t ]+",
            re.IGNORECASE,
        ),
    ),
)

TEXT_SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".txt",
    ".gitignore",
}


def is_text_file(path: Path) -> bool:
    return (
        path.name == ".gitignore"
        or path.suffix.lower() in TEXT_SUFFIXES
    )


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED:
        if not (ROOT / rel).exists():
            failures.append(
                f"missing required file: {rel}"
            )

    for path in ROOT.rglob("*"):
        rel = path.relative_to(
            ROOT
        )

        if "__pycache__" in rel.parts:
            failures.append(
                f"compiled Python cache present: {rel}"
            )
            continue

        if (
            rel.parts
            and rel.parts[
                0
            ]
            in FORBIDDEN_ROOT_ENTRIES
        ):
            failures.append(
                f"runtime/private root entry present: {rel}"
            )
            continue

        if (
            path.is_file()
            and path.suffix.lower()
            in FORBIDDEN_SUFFIXES
        ):
            failures.append(
                f"forbidden generated file: {rel}"
            )
            continue

        if not (
            path.is_file()
            and is_text_file(
                path
            )
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue

        for label, pattern in SECRET_PATTERNS:
            match = pattern.search(
                text
            )
            if match:
                failures.append(
                    f"{label} found in {rel}"
                )

    # Generic examples are allowed, but an unexpected Riot-ID-shaped literal
    # in the public source can indicate a personal fallback accidentally leaked.
    allowed_riot_ids = {
        "Player#EUNE",
    }
    riot_id_pattern = re.compile(
        r"\\b[A-Za-z0-9_. -]{3,20}#[A-Za-z0-9]{3,6}\\b"
    )
    for path in ROOT.rglob("*"):
        if not (
            path.is_file()
            and is_text_file(
                path
            )
        ):
            continue
        try:
            text = path.read_text(
                encoding="utf-8"
            )
        except Exception:
            continue
        for match in riot_id_pattern.findall(
            text
        ):
            value = match.strip()
            if (
                value
                and value not in allowed_riot_ids
            ):
                failures.append(
                    f"unexpected Riot-ID-shaped literal in {path.relative_to(ROOT)}: {value}"
                )

    if failures:
        print(
            "PUBLIC SOURCE AUDIT: FAIL"
        )
        for failure in sorted(
            set(
                failures
            )
        ):
            print(
                f"- {failure}"
            )
        return 1

    print(
        "PUBLIC SOURCE AUDIT: PASS"
    )
    print(
        "No API-key-shaped secrets, literal Windows user paths, "
        "runtime data, logs, caches, or compiled artifacts detected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
