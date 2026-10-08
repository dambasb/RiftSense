from __future__ import annotations

import copy
from contextlib import contextmanager
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}
_ACTIVITY_CONDITION = threading.Condition(threading.RLock())
_ACTIVE_OPERATIONS = 0
_MAINTENANCE_OWNER: int | None = None
_MAINTENANCE_DEPTH = 0


@contextmanager
def _storage_operation():
    """Register one ordinary persistence operation with the maintenance gate."""
    global _ACTIVE_OPERATIONS
    thread_id = threading.get_ident()
    with _ACTIVITY_CONDITION:
        while (
            _MAINTENANCE_OWNER is not None
            and _MAINTENANCE_OWNER != thread_id
        ):
            _ACTIVITY_CONDITION.wait()
        _ACTIVE_OPERATIONS += 1
    try:
        yield
    finally:
        with _ACTIVITY_CONDITION:
            _ACTIVE_OPERATIONS -= 1
            if _ACTIVE_OPERATIONS == 0:
                _ACTIVITY_CONDITION.notify_all()


@contextmanager
def persistence_maintenance(timeout: float | None = None):
    """Exclude other JSON operations during a logical backup transaction.

    Normal operations still use independent per-file locks. Only an explicit
    maintenance transaction waits for current operations and temporarily
    prevents new operations from other threads. The owner may call storage
    APIs reentrantly while applying or rolling back a restore.
    """
    global _MAINTENANCE_OWNER, _MAINTENANCE_DEPTH
    thread_id = threading.get_ident()
    deadline = (
        None
        if timeout is None
        else time.monotonic() + max(0.0, float(timeout))
    )
    with _ACTIVITY_CONDITION:
        if _MAINTENANCE_OWNER == thread_id:
            _MAINTENANCE_DEPTH += 1
        else:
            while _MAINTENANCE_OWNER is not None or _ACTIVE_OPERATIONS:
                if deadline is None:
                    _ACTIVITY_CONDITION.wait()
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        "Timed out waiting for persistence operations to finish."
                    )
                _ACTIVITY_CONDITION.wait(remaining)
            _MAINTENANCE_OWNER = thread_id
            _MAINTENANCE_DEPTH = 1
    try:
        yield
    finally:
        with _ACTIVITY_CONDITION:
            _MAINTENANCE_DEPTH -= 1
            if _MAINTENANCE_DEPTH == 0:
                _MAINTENANCE_OWNER = None
                _ACTIVITY_CONDITION.notify_all()


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(Path(path))))


def _path_lock(path: Path) -> threading.RLock:
    key = _path_key(path)
    with _LOCKS_GUARD:
        lock = _PATH_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PATH_LOCKS[key] = lock
        return lock


def _fresh_default(default: Any) -> Any:
    value = {} if default is None else default
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


def _corrupt_path(target: Path) -> Path:
    timestamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    return target.with_name(
        f"{target.name}.corrupt-{timestamp}-{uuid.uuid4().hex[:8]}"
    )


def _preserve_corrupt_unlocked(target: Path, error: Exception) -> None:
    if not target.exists():
        return
    preserved = _corrupt_path(target)
    try:
        os.replace(target, preserved)
        LOGGER.warning(
            "Invalid JSON preserved at %s before defaults were used: %s",
            preserved,
            error,
        )
    except OSError as preserve_error:
        LOGGER.warning(
            "Invalid JSON at %s could not be preserved separately (%s): %s",
            target,
            preserve_error,
            error,
        )


def _read_json_unlocked(
    target: Path,
    default: Any,
    *,
    preserve_corrupt: bool,
) -> Any:
    try:
        with target.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return _fresh_default(default)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        if preserve_corrupt:
            _preserve_corrupt_unlocked(target, exc)
        return _fresh_default(default)
    except (OSError, TypeError, ValueError):
        return _fresh_default(default)


def read_json(
    path: Path,
    default: Any = None,
    *,
    preserve_corrupt: bool = True,
) -> Any:
    """Read JSON while excluding same-process writers for this exact path.

    Missing files retain the historical default behavior. Invalid UTF-8/JSON is
    moved aside with a unique ``.corrupt-*`` suffix before the default is
    returned, so recovery never silently destroys the only damaged evidence.
    """
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            return _read_json_unlocked(
                target,
                default,
                preserve_corrupt=preserve_corrupt,
            )


def load_json(path: Path, default: Any = None) -> Any:
    """Backward-compatible alias for :func:`read_json`."""
    return read_json(path, default)


def _fsync_parent_directory(target: Path) -> None:
    """Best-effort directory flush (supported on POSIX, usually not Windows)."""
    flags = getattr(os, "O_RDONLY", 0)
    directory_fd = None
    try:
        directory_fd = os.open(target.parent, flags)
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        if directory_fd is not None:
            os.close(directory_fd)


def _write_json_atomic_unlocked(target: Path, payload: Any) -> tuple[bool, str]:
    temp: Path | None = None
    try:
        serialized = json.dumps(payload, ensure_ascii=False, indent=2)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(
            f".{target.name}.{os.getpid()}.{threading.get_ident()}."
            f"{uuid.uuid4().hex}.tmp"
        )
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())

        try:
            if target.exists():
                os.chmod(temp, target.stat().st_mode)
        except OSError:
            pass

        os.replace(temp, target)
        _fsync_parent_directory(target)
        return True, ""
    except (OSError, TypeError, ValueError) as exc:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        return False, str(exc)


def write_json_atomic(path: Path, payload: Any) -> tuple[bool, str]:
    """Flush JSON to a unique sibling temp file, then atomically replace it."""
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            return _write_json_atomic_unlocked(target, payload)


def _write_json_bytes_atomic_unlocked(
    target: Path,
    payload: bytes,
    *,
    validate: bool,
) -> tuple[bool, str]:
    temp: Path | None = None
    try:
        if validate:
            json.loads(payload.decode("utf-8"))
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(
            f".{target.name}.{os.getpid()}.{threading.get_ident()}."
            f"{uuid.uuid4().hex}.tmp"
        )
        with temp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            if target.exists():
                os.chmod(temp, target.stat().st_mode)
        except OSError:
            pass
        os.replace(temp, target)
        _fsync_parent_directory(target)
        return True, ""
    except (json.JSONDecodeError, UnicodeDecodeError, OSError, TypeError) as exc:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
        return False, str(exc)


def write_json_bytes_atomic(
    path: Path,
    payload: bytes,
    *,
    validate: bool = True,
) -> tuple[bool, str]:
    """Atomically replace JSON with exact UTF-8 bytes.

    Restore uses this variant so checksums and rollback snapshots remain
    byte-for-byte stable. Validation may only be disabled for rollback bytes
    captured from that same live path before the transaction began.
    """
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            return _write_json_bytes_atomic_unlocked(
                target,
                payload,
                validate=validate,
            )


def write_json_atomic_if_missing(path: Path, payload: Any) -> tuple[bool, str]:
    """Atomically create JSON only when no destination already exists."""
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            if target.exists():
                return False, "destination exists"
            return _write_json_atomic_unlocked(target, payload)


def update_json(
    path: Path,
    updater: Callable[[Any], Any],
    default: Any = None,
    *,
    preserve_corrupt: bool = True,
) -> tuple[bool, str]:
    """Lock one file across its complete read-modify-write transaction.

    ``updater`` may mutate its argument and return ``None``, or return a
    replacement value. An unchanged value is not rewritten.
    """
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            current = _read_json_unlocked(
                target,
                default,
                preserve_corrupt=preserve_corrupt,
            )
            before = _fresh_default(current)
            try:
                replacement = updater(current)
                updated = current if replacement is None else replacement
            except Exception as exc:
                return False, str(exc)
            if updated == before and target.exists():
                return True, ""
            return _write_json_atomic_unlocked(target, updated)


def delete_json(path: Path) -> tuple[bool, str]:
    """Delete a JSON file while excluding same-process readers and writers."""
    target = Path(path)
    with _storage_operation():
        with _path_lock(target):
            try:
                target.unlink(missing_ok=True)
                _fsync_parent_directory(target)
                return True, ""
            except OSError as exc:
                return False, str(exc)


def wait_for_json_idle(timeout: float = 2.0) -> bool:
    """Best-effort shutdown barrier for JSON transactions already in flight."""
    deadline = time.monotonic() + max(0.0, float(timeout))
    with _ACTIVITY_CONDITION:
        while _ACTIVE_OPERATIONS or _MAINTENANCE_OWNER is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            _ACTIVITY_CONDITION.wait(remaining)
        return True
