#!/usr/bin/env python3
"""
RiftSense pre-push recommendation item audit.

Run from the extracted RiftSense source tree:

    python tools/pre_push_audit.py

The script downloads/uses the latest Riot Data Dragon item catalogue, collects
every static/cached item name that can feed the build engine, and exits non-zero
if any candidate fails RiftSense's current Summoner's Rift validator.

No Riot API key is required and no user match history is read.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "RiftSense.py"

# importlib does not automatically add the app root to sys.path when loading a
# file by path. RiftSense imports its extracted ``riftsense`` package, so make
# the source root explicit for this standalone audit tool.
root_text = str(ROOT)
if root_text not in sys.path:
    sys.path.insert(0, root_text)

# Keep the audit isolated from the user's normal RiftSense data directory.
AUDIT_LOCALAPPDATA = Path(
    tempfile.mkdtemp(
        prefix="riftsense-prepush-"
    )
)
os.environ["LOCALAPPDATA"] = str(
    AUDIT_LOCALAPPDATA
)

spec = importlib.util.spec_from_file_location(
    "riftsense_prepush",
    APP_PATH,
)
if spec is None or spec.loader is None:
    raise SystemExit(
        "Could not load RiftSense.py"
    )

rs = importlib.util.module_from_spec(
    spec
)
spec.loader.exec_module(
    rs
)

dd = rs.DataDragon()
version = dd.resolve_version(
    ""
)
if not version:
    raise SystemExit(
        "FAIL: could not resolve a Riot Data Dragon version."
    )

if not dd.load_items(
    version
):
    raise SystemExit(
        f"FAIL: could not load Data Dragon items for {version}."
    )

report = rs.audit_recommendation_items(
    dd
)

print(
    f"RiftSense item audit • patch {report['patch']}"
)
print(
    f"Candidates: {report['total']}"
)
print(
    f"Valid: {len(report['valid'])}"
)
print(
    f"Invalid: {len(report['invalid'])}"
)

if report[
    "invalid"
]:
    print()
    print(
        "INVALID RECOMMENDATION CANDIDATES"
    )
    for row in report[
        "invalid"
    ]:
        print(
            f"- {row['name']}: {row['reason']}"
        )
        print(
            "  Sources: "
            + ", ".join(
                row[
                    "sources"
                ]
            )
        )
    raise SystemExit(
        1
    )

print(
    "PASS: every recommendation candidate is a current "
    "Summoner's Rift item."
)
raise SystemExit(
    0
)
