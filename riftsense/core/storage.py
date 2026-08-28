from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any = None) -> Any:
    """Load UTF-8 JSON; return the provided default when data is unavailable or invalid."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {} if default is None else default


def write_json_atomic(path: Path, payload: Any) -> tuple[bool, str]:
    """Atomically replace a JSON file through a sibling temporary file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    try:
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(target)
        return True, ""
    except (OSError, TypeError, ValueError) as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        return False, str(exc)
