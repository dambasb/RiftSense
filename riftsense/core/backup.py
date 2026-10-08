from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import threading
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Callable

from .storage import (
    delete_json,
    persistence_maintenance,
    write_json_bytes_atomic,
)


BACKUP_FORMAT_VERSION = 4
MANIFEST_NAME = "backup_manifest.json"
MAX_ARCHIVE_FILES = 10_000
MAX_MEMBER_SIZE = 128 * 1024 * 1024
MAX_ARCHIVE_SIZE = 512 * 1024 * 1024
MAX_MANIFEST_SIZE = 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMPONENT_KINDS = {
    "settings.json": "file",
    "history": "directory",
    "player_memory.json": "file",
    "performance_history.json": "file",
    "rank_progress.json": "file",
    "ai_reviews": "directory",
}
_COMPONENT_ORDER = tuple(_COMPONENT_KINDS)

JsonTransform = Callable[[str, Any], Any]
FailureInjector = Callable[[str, str | None], None]
_NO_VIRTUAL_SETTINGS = object()


class BackupError(Exception):
    """Base class for backup creation and validation failures."""


class BackupValidationError(BackupError):
    """Raised when an archive is unsafe, damaged, or incompatible."""


class RestoreTransactionError(BackupError):
    """Raised after a restore fails, with rollback outcome attached."""

    def __init__(
        self,
        message: str,
        *,
        rollback_performed: bool,
        recovery_path: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.rollback_performed = rollback_performed
        self.recovery_path = recovery_path


@dataclass(frozen=True)
class BackupLayout:
    settings: Path
    history: Path
    player_memory: Path
    performance_history: Path
    rank_progress: Path
    ai_reviews: Path

    def components(self) -> dict[str, Path]:
        return {
            "settings.json": Path(self.settings),
            "history": Path(self.history),
            "player_memory.json": Path(self.player_memory),
            "performance_history.json": Path(self.performance_history),
            "rank_progress.json": Path(self.rank_progress),
            "ai_reviews": Path(self.ai_reviews),
        }

    @property
    def data_root(self) -> Path:
        return Path(self.settings).parent


@dataclass(frozen=True)
class ValidatedBackup:
    source: Path
    staging_root: Path
    files: tuple[str, ...]
    components: dict[str, bool]
    manifest: dict[str, Any] | None
    legacy: bool


@dataclass(frozen=True)
class RestoreResult:
    legacy: bool
    restored_files: int
    safety_backup: Path | None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_member_name(name: str) -> tuple[str, bool]:
    if not isinstance(name, str) or not name or "\x00" in name:
        raise BackupValidationError("Backup contains an empty or invalid path.")
    if name.startswith(("/", "\\")):
        raise BackupValidationError(f"Backup contains an absolute path: {name}")
    windows_path = PureWindowsPath(name)
    if windows_path.is_absolute() or windows_path.drive:
        raise BackupValidationError(f"Backup contains a drive path: {name}")

    normalized = name.replace("\\", "/")
    is_directory = normalized.endswith("/")
    normalized = normalized.rstrip("/")
    if not normalized:
        raise BackupValidationError("Backup contains an invalid root entry.")
    parts = PurePosixPath(normalized).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise BackupValidationError(f"Backup contains an unsafe path: {name}")
    if any(":" in part for part in parts):
        raise BackupValidationError(f"Backup contains an unsafe path: {name}")
    return "/".join(parts), is_directory


def _component_for_path(relative_path: str) -> str | None:
    if relative_path in _COMPONENT_KINDS:
        return relative_path
    for component in ("history", "ai_reviews"):
        if relative_path.startswith(component + "/"):
            return component
    return None


def _allowed_member(relative_path: str, is_directory: bool) -> bool:
    if relative_path == MANIFEST_NAME:
        return not is_directory
    component = _component_for_path(relative_path)
    if component is None:
        return False
    if _COMPONENT_KINDS[component] == "file":
        return relative_path == component and not is_directory
    return relative_path == component or relative_path.startswith(component + "/")


def _is_excluded_source(path: Path) -> bool:
    name = path.name.casefold()
    return ".corrupt-" in name or name.endswith(".tmp")


def _validate_json_bytes(relative_path: str, payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise BackupValidationError(
            f"Backup JSON is invalid: {relative_path}: {exc}"
        ) from exc


def _validate_manifest(
    manifest: Any,
    actual_files: dict[str, bytes],
) -> tuple[dict[str, bool], bool]:
    if not isinstance(manifest, dict):
        raise BackupValidationError("Backup manifest must be a JSON object.")

    format_version = manifest.get("format_version")
    if format_version is None:
        legacy_format = manifest.get("format")
        if type(legacy_format) is not int or legacy_format not in {1, 2, 3}:
            raise BackupValidationError("Backup manifest format is unsupported.")
        if manifest.get("app", "RiftSense") != "RiftSense":
            raise BackupValidationError("Backup was created by an incompatible application.")
        return _legacy_components(actual_files), True

    if format_version != BACKUP_FORMAT_VERSION:
        raise BackupValidationError(
            f"Backup format {format_version!r} is not supported by this RiftSense build."
        )
    if manifest.get("app") != "RiftSense":
        raise BackupValidationError("Backup was created by an incompatible application.")
    if (
        not isinstance(manifest.get("application_version"), str)
        or not manifest["application_version"].strip()
    ):
        raise BackupValidationError("Backup manifest has no valid application version.")
    created_at = manifest.get("created_at")
    if not isinstance(created_at, str):
        raise BackupValidationError("Backup manifest has no valid creation timestamp.")
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BackupValidationError(
            "Backup manifest creation timestamp is invalid."
        ) from exc

    components = manifest.get("components")
    if (
        not isinstance(components, dict)
        or set(components) != set(_COMPONENT_KINDS)
        or any(type(value) is not bool for value in components.values())
    ):
        raise BackupValidationError("Backup manifest component inventory is invalid.")
    if components.get("settings.json") is not True:
        raise BackupValidationError("Modern backups must contain settings.json.")

    listed = manifest.get("files")
    if not isinstance(listed, list):
        raise BackupValidationError("Backup manifest file list is invalid.")
    expected: dict[str, tuple[int, str]] = {}
    folded: set[str] = set()
    for entry in listed:
        if not isinstance(entry, dict):
            raise BackupValidationError("Backup manifest contains an invalid file entry.")
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            raise BackupValidationError("Backup manifest contains an invalid file path.")
        path_value, is_directory = _normalize_member_name(path_value)
        if is_directory or path_value == MANIFEST_NAME or not _allowed_member(path_value, False):
            raise BackupValidationError(
                f"Backup manifest contains an unexpected file: {path_value}"
            )
        key = path_value.casefold()
        if key in folded:
            raise BackupValidationError(
                f"Backup manifest contains a duplicate file: {path_value}"
            )
        folded.add(key)
        size = entry.get("size")
        checksum = entry.get("sha256")
        if type(size) is not int or size < 0 or size > MAX_MEMBER_SIZE:
            raise BackupValidationError(
                f"Backup manifest has an invalid size for {path_value}."
            )
        if not isinstance(checksum, str) or not _SHA256_RE.fullmatch(checksum):
            raise BackupValidationError(
                f"Backup manifest has an invalid checksum for {path_value}."
            )
        expected[path_value] = (size, checksum)

    if set(expected) != set(actual_files):
        missing = sorted(set(expected) - set(actual_files))
        unexpected = sorted(set(actual_files) - set(expected))
        detail = f"missing={missing}, unexpected={unexpected}"
        raise BackupValidationError(f"Backup manifest does not match archive files: {detail}")
    for relative_path, payload in actual_files.items():
        size, checksum = expected[relative_path]
        if len(payload) != size:
            raise BackupValidationError(
                f"Backup size check failed for {relative_path}."
            )
        if _sha256(payload) != checksum:
            raise BackupValidationError(
                f"Backup checksum check failed for {relative_path}."
            )

    for component, present in components.items():
        if _COMPONENT_KINDS[component] == "file":
            actual_present = component in actual_files
        else:
            actual_present = any(
                path.startswith(component + "/") for path in actual_files
            )
            # An empty directory is represented only by the component flag.
            if present and not actual_present:
                actual_present = True
        if present != actual_present:
            raise BackupValidationError(
                f"Backup component inventory conflicts with {component}."
            )
    return dict(components), False


def _legacy_components(actual_files: dict[str, bytes]) -> dict[str, bool]:
    components: dict[str, bool] = {}
    for component, kind in _COMPONENT_KINDS.items():
        if kind == "file":
            components[component] = component in actual_files
        else:
            components[component] = any(
                path.startswith(component + "/") for path in actual_files
            )
    if not (
        components["settings.json"]
        or components["player_memory.json"]
        or components["history"]
    ):
        raise BackupValidationError(
            "Legacy ZIP does not contain enough recognizable RiftSense state."
        )
    return components


def validate_backup(source: Path, staging_root: Path) -> ValidatedBackup:
    """Fully validate and safely stage an archive without touching live state."""
    source = Path(source)
    staging_root = Path(staging_root)
    if not zipfile.is_zipfile(source):
        raise BackupValidationError("Selected file is not a readable ZIP archive.")
    staging_root.mkdir(parents=True, exist_ok=True)

    actual_files: dict[str, bytes] = {}
    directory_entries: set[str] = set()
    seen: dict[str, str] = {}
    file_names: set[str] = set()
    manifest_payload: bytes | None = None
    try:
        with zipfile.ZipFile(source, "r") as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_FILES:
                raise BackupValidationError("Backup contains too many archive members.")
            total_size = 0
            for info in infos:
                relative_path, named_directory = _normalize_member_name(info.filename)
                is_directory = info.is_dir() or named_directory
                folded = relative_path.casefold()
                if folded in seen:
                    raise BackupValidationError(
                        f"Backup contains duplicate paths: {seen[folded]} and {relative_path}"
                    )
                seen[folded] = relative_path
                if not _allowed_member(relative_path, is_directory):
                    raise BackupValidationError(
                        f"Unexpected file or directory in backup: {relative_path}"
                    )
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise BackupValidationError(
                        f"Backup contains a symbolic-link member: {relative_path}"
                    )
                if info.flag_bits & 0x1:
                    raise BackupValidationError("Encrypted backup members are not supported.")
                if is_directory:
                    directory_entries.add(relative_path)
                    continue
                if info.file_size > MAX_MEMBER_SIZE:
                    raise BackupValidationError(
                        f"Backup member is unreasonably large: {relative_path}"
                    )
                total_size += info.file_size
                if total_size > MAX_ARCHIVE_SIZE:
                    raise BackupValidationError("Backup expands beyond the safe size limit.")
                if (
                    info.file_size > 10 * 1024 * 1024
                    and info.file_size > max(1, info.compress_size) * MAX_COMPRESSION_RATIO
                ):
                    raise BackupValidationError(
                        f"Backup member has an unsafe compression ratio: {relative_path}"
                    )
                payload = archive.read(info)
                if len(payload) != info.file_size:
                    raise BackupValidationError(
                        f"Backup member size is inconsistent: {relative_path}"
                    )
                file_names.add(relative_path)
                if relative_path == MANIFEST_NAME:
                    if len(payload) > MAX_MANIFEST_SIZE:
                        raise BackupValidationError("Backup manifest is too large.")
                    manifest_payload = payload
                else:
                    actual_files[relative_path] = payload

            corrupt_member = archive.testzip()
            if corrupt_member is not None:
                raise BackupValidationError(
                    f"Backup CRC validation failed for {corrupt_member}."
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, BackupValidationError):
            raise
        raise BackupValidationError(f"Backup archive is unreadable: {exc}") from exc

    for file_name in file_names:
        prefix = file_name.casefold() + "/"
        if any(other.casefold().startswith(prefix) for other in seen.values()):
            raise BackupValidationError(
                f"Backup has a file/directory path conflict at {file_name}."
            )
    for directory_name in directory_entries:
        if directory_name in file_names:
            raise BackupValidationError(
                f"Backup has a file/directory path conflict at {directory_name}."
            )

    manifest: dict[str, Any] | None = None
    if manifest_payload is not None:
        parsed_manifest = _validate_json_bytes(MANIFEST_NAME, manifest_payload)
        components, legacy = _validate_manifest(parsed_manifest, actual_files)
        manifest = parsed_manifest
    else:
        components = _legacy_components(actual_files)
        legacy = True

    if not legacy:
        for directory_name in directory_entries:
            component = _component_for_path(directory_name)
            if component is None or not components[component]:
                raise BackupValidationError(
                    f"Backup directory conflicts with its manifest: {directory_name}"
                )

    for relative_path, payload in actual_files.items():
        if relative_path.casefold().endswith(".json"):
            _validate_json_bytes(relative_path, payload)
        target = staging_root.joinpath(*PurePosixPath(relative_path).parts)
        resolved = target.resolve()
        try:
            resolved.relative_to(staging_root.resolve())
        except ValueError as exc:
            raise BackupValidationError(
                f"Backup path escapes staging root: {relative_path}"
            ) from exc
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(payload)

    return ValidatedBackup(
        source=source,
        staging_root=staging_root,
        files=tuple(sorted(actual_files)),
        components=components,
        manifest=manifest,
        legacy=legacy,
    )


def _serialize_json_for_backup(
    relative_path: str,
    payload: bytes,
    transform_json: JsonTransform | None,
) -> bytes:
    parsed = _validate_json_bytes(relative_path, payload)
    if transform_json is not None:
        parsed = transform_json(relative_path, parsed)
    try:
        return json.dumps(parsed, ensure_ascii=False, indent=2).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BackupError(
            f"JSON transformation made {relative_path} unserializable: {exc}"
        ) from exc


def _collect_backup_snapshot(
    layout: BackupLayout,
    transform_json: JsonTransform | None,
    virtual_settings: Any,
) -> tuple[dict[str, bytes], dict[str, bool]]:
    files: dict[str, bytes] = {}
    components: dict[str, bool] = {}
    for component in _COMPONENT_ORDER:
        source = layout.components()[component]
        kind = _COMPONENT_KINDS[component]
        if source.is_symlink():
            raise BackupError(f"Refusing to back up symbolic link: {source}")
        if not source.exists():
            if component == "settings.json" and virtual_settings is not _NO_VIRTUAL_SETTINGS:
                try:
                    payload = json.dumps(
                        virtual_settings,
                        ensure_ascii=False,
                    ).encode("utf-8")
                except (TypeError, ValueError) as exc:
                    raise BackupError(f"Current settings cannot be backed up: {exc}") from exc
                files[component] = _serialize_json_for_backup(
                    component,
                    payload,
                    transform_json,
                )
                components[component] = True
                continue
            components[component] = False
            continue
        if kind == "file":
            if not source.is_file():
                raise BackupError(f"Backup component is not a file: {source}")
            payload = source.read_bytes()
            if component.endswith(".json"):
                payload = _serialize_json_for_backup(
                    component,
                    payload,
                    transform_json,
                )
            files[component] = payload
            components[component] = True
            continue

        if not source.is_dir():
            raise BackupError(f"Backup component is not a directory: {source}")
        components[component] = True
        for path in sorted(source.rglob("*"), key=lambda value: value.as_posix().casefold()):
            if path.is_symlink():
                raise BackupError(f"Refusing to back up symbolic link: {path}")
            if not path.is_file() or _is_excluded_source(path):
                continue
            relative_path = component + "/" + path.relative_to(source).as_posix()
            payload = path.read_bytes()
            if relative_path.casefold().endswith(".json"):
                payload = _serialize_json_for_backup(
                    relative_path,
                    payload,
                    transform_json,
                )
            files[relative_path] = payload

    if not components.get("settings.json"):
        raise BackupError("Cannot create a complete backup without settings.json.")
    total_size = sum(len(payload) for payload in files.values())
    if len(files) > MAX_ARCHIVE_FILES or total_size > MAX_ARCHIVE_SIZE:
        raise BackupError("Current user data exceeds safe backup limits.")
    return files, components


def _fsync_parent(path: Path) -> None:
    descriptor = None
    try:
        descriptor = os.open(path.parent, getattr(os, "O_RDONLY", 0))
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def create_backup(
    layout: BackupLayout,
    destination: Path,
    *,
    application_version: str,
    transform_json: JsonTransform | None = None,
    virtual_settings: Any = _NO_VIRTUAL_SETTINGS,
) -> Path:
    """Create and self-validate an atomically published coherent backup."""
    destination = Path(destination)
    resolved_destination = destination.resolve()
    for component, source in layout.components().items():
        resolved_source = source.resolve()
        if _COMPONENT_KINDS[component] == "file":
            if resolved_destination == resolved_source:
                raise BackupError("Backup destination overlaps live user state.")
            continue
        try:
            resolved_destination.relative_to(resolved_source)
        except ValueError:
            continue
        raise BackupError("Backup destination cannot be inside backup-managed data.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with persistence_maintenance(timeout=15.0):
        files, components = _collect_backup_snapshot(
            layout,
            transform_json,
            virtual_settings,
        )

    manifest = {
        "app": "RiftSense",
        "application_version": str(application_version),
        "format_version": BACKUP_FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "components": components,
        "files": [
            {
                "path": relative_path,
                "size": len(files[relative_path]),
                "sha256": _sha256(files[relative_path]),
            }
            for relative_path in sorted(files)
        ],
    }
    temp_path = destination.with_name(
        f".{destination.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with zipfile.ZipFile(
            temp_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            for relative_path in sorted(files):
                archive.writestr(relative_path, files[relative_path])
        with temp_path.open("r+b") as handle:
            os.fsync(handle.fileno())
        with tempfile.TemporaryDirectory(prefix="riftsense-backup-check-") as check_dir:
            validate_backup(temp_path, Path(check_dir))
        os.replace(temp_path, destination)
        _fsync_parent(destination)
        return destination
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.restore.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        _fsync_parent(path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def _remove_live_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        if path.suffix.casefold() == ".json" and not path.is_symlink():
            ok, error = delete_json(path)
            if not ok:
                raise OSError(error)
        else:
            path.unlink()
        return
    for child in sorted(path.rglob("*"), key=lambda value: len(value.parts), reverse=True):
        if child.is_symlink() or child.is_file():
            if child.suffix.casefold() == ".json" and not child.is_symlink():
                ok, error = delete_json(child)
                if not ok:
                    raise OSError(error)
            else:
                child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _snapshot_components(
    layout: BackupLayout,
    components: tuple[str, ...],
    rollback_root: Path,
) -> tuple[dict[str, str], dict[str, Any]]:
    states: dict[str, str] = {}
    for component in components:
        source = layout.components()[component]
        target = rollback_root / component
        if source.is_symlink():
            raise BackupError(f"Live backup state contains a symbolic link: {source}")
        if not source.exists():
            states[component] = "missing"
        elif source.is_file():
            if _COMPONENT_KINDS[component] != "file":
                raise BackupError(f"Live backup component has the wrong type: {source}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            states[component] = "file"
        elif source.is_dir():
            if _COMPONENT_KINDS[component] != "directory":
                raise BackupError(f"Live backup component has the wrong type: {source}")
            for path in source.rglob("*"):
                if path.is_symlink():
                    raise BackupError(f"Live backup state contains a symbolic link: {path}")
            shutil.copytree(source, target)
            states[component] = "directory"
        else:
            raise BackupError(f"Live backup component cannot be preserved: {source}")
    return states, _logical_state(layout, components)


def _logical_state(layout: BackupLayout, components: tuple[str, ...]) -> dict[str, Any]:
    state: dict[str, Any] = {}
    for component in components:
        path = layout.components()[component]
        if path.is_symlink():
            state[component] = ("symlink", os.readlink(path))
        elif not path.exists():
            state[component] = ("missing",)
        elif path.is_file():
            payload = path.read_bytes()
            state[component] = ("file", len(payload), _sha256(payload))
        elif path.is_dir():
            entries: list[tuple[Any, ...]] = []
            for child in sorted(path.rglob("*"), key=lambda value: value.as_posix()):
                relative = child.relative_to(path).as_posix()
                if child.is_symlink():
                    entries.append(("symlink", relative, os.readlink(child)))
                elif child.is_dir():
                    entries.append(("directory", relative))
                elif child.is_file():
                    payload = child.read_bytes()
                    entries.append(("file", relative, len(payload), _sha256(payload)))
            state[component] = ("directory", tuple(entries))
    return state


def _write_live_file(path: Path, payload: bytes, *, validate_json: bool) -> None:
    if path.suffix.casefold() == ".json":
        ok, error = write_json_bytes_atomic(path, payload, validate=validate_json)
        if not ok:
            raise OSError(error)
    else:
        _atomic_write_bytes(path, payload)


def _rollback(
    layout: BackupLayout,
    components: tuple[str, ...],
    rollback_root: Path,
    states: dict[str, str],
) -> None:
    for component in components:
        _remove_live_path(layout.components()[component])
    for component in components:
        state = states[component]
        destination = layout.components()[component]
        source = rollback_root / component
        if state == "missing":
            continue
        if state == "file":
            _write_live_file(destination, source.read_bytes(), validate_json=False)
            continue
        destination.mkdir(parents=True, exist_ok=True)
        directories = [path for path in source.rglob("*") if path.is_dir()]
        for directory in sorted(directories, key=lambda value: len(value.parts)):
            (destination / directory.relative_to(source)).mkdir(parents=True, exist_ok=True)
        for path in sorted(source.rglob("*"), key=lambda value: value.as_posix()):
            if path.is_file():
                target = destination / path.relative_to(source)
                _write_live_file(target, path.read_bytes(), validate_json=False)


def _invoke_failure(
    failure_injector: FailureInjector | None,
    stage: str,
    relative_path: str | None = None,
) -> None:
    if failure_injector is not None:
        failure_injector(stage, relative_path)


def _transform_staged_json(
    plan: ValidatedBackup,
    transform_json: JsonTransform | None,
) -> None:
    if transform_json is None:
        return
    for relative_path in plan.files:
        if not relative_path.casefold().endswith(".json"):
            continue
        path = plan.staging_root.joinpath(*PurePosixPath(relative_path).parts)
        parsed = _validate_json_bytes(relative_path, path.read_bytes())
        original = json.dumps(parsed, ensure_ascii=False, indent=2).encode("utf-8")
        transformed = transform_json(relative_path, parsed)
        updated = json.dumps(
            transformed,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
        if updated == original:
            continue
        if not plan.legacy:
            raise BackupValidationError(
                f"Modern backup contains disallowed persisted data: {relative_path}"
            )
        path.write_bytes(updated)


def _apply_staged(
    plan: ValidatedBackup,
    layout: BackupLayout,
    selected_components: tuple[str, ...],
    failure_injector: FailureInjector | None,
) -> int:
    for component in selected_components:
        _remove_live_path(layout.components()[component])

    for component in selected_components:
        if (
            _COMPONENT_KINDS[component] == "directory"
            and plan.components[component]
        ):
            layout.components()[component].mkdir(parents=True, exist_ok=True)

    selected_files = [
        relative_path
        for relative_path in plan.files
        if _component_for_path(relative_path) in selected_components
    ]
    midpoint = max(1, (len(selected_files) + 1) // 2)
    for index, relative_path in enumerate(selected_files, start=1):
        component = _component_for_path(relative_path)
        assert component is not None
        if component == relative_path:
            destination = layout.components()[component]
        else:
            suffix = PurePosixPath(relative_path).relative_to(component)
            destination = layout.components()[component].joinpath(*suffix.parts)
        source = plan.staging_root.joinpath(*PurePosixPath(relative_path).parts)
        _invoke_failure(failure_injector, "before_atomic_replace", relative_path)
        _write_live_file(destination, source.read_bytes(), validate_json=True)
        if index == 1:
            _invoke_failure(
                failure_injector,
                "after_first_restored_file",
                relative_path,
            )
        if index == midpoint:
            _invoke_failure(failure_injector, "halfway", relative_path)
        _invoke_failure(failure_injector, "after_restored_file", relative_path)
    return len(selected_files)


def _verify_restored(
    plan: ValidatedBackup,
    layout: BackupLayout,
    failure_injector: FailureInjector | None = None,
) -> None:
    expected_files = set(plan.files)
    for index, relative_path in enumerate(plan.files):
        component = _component_for_path(relative_path)
        assert component is not None
        if component == relative_path:
            live_path = layout.components()[component]
        else:
            suffix = PurePosixPath(relative_path).relative_to(component)
            live_path = layout.components()[component].joinpath(*suffix.parts)
        if not live_path.is_file() or live_path.is_symlink():
            raise BackupError(f"Restored file is missing: {relative_path}")
        payload = live_path.read_bytes()
        if relative_path.casefold().endswith(".json"):
            _validate_json_bytes(relative_path, payload)
        staged_payload = plan.staging_root.joinpath(
            *PurePosixPath(relative_path).parts
        ).read_bytes()
        if payload != staged_payload:
            raise BackupError(f"Restored file verification failed: {relative_path}")
        if index == 0:
            _invoke_failure(
                failure_injector,
                "during_verification",
                relative_path,
            )

    if plan.legacy:
        return
    for component in _COMPONENT_ORDER:
        live_path = layout.components()[component]
        present = plan.components[component]
        if _COMPONENT_KINDS[component] == "file":
            if live_path.exists() != present:
                raise BackupError(f"Restored component state is wrong: {component}")
            continue
        if present and not live_path.is_dir():
            raise BackupError(f"Restored directory is missing: {component}")
        if not present and live_path.exists():
            raise BackupError(f"Unexpected restored directory exists: {component}")
        if present:
            actual = {
                component + "/" + path.relative_to(live_path).as_posix()
                for path in live_path.rglob("*")
                if path.is_file()
            }
            expected = {
                path for path in expected_files if path.startswith(component + "/")
            }
            if actual != expected:
                raise BackupError(
                    f"Restored directory contains unexpected files: {component}"
                )


def restore_backup_transactional(
    source: Path,
    layout: BackupLayout,
    *,
    application_version: str,
    transform_json: JsonTransform | None = None,
    safety_backup: Path | None = None,
    safety_virtual_settings: Any = _NO_VIRTUAL_SETTINGS,
    failure_injector: FailureInjector | None = None,
    recovery_parent: Path | None = None,
) -> RestoreResult:
    """Validate, stage, apply, verify, and commit or fully roll back restore."""
    work_root = Path(tempfile.mkdtemp(prefix="riftsense-restore-"))
    staging_root = work_root / "staging"
    rollback_root = work_root / "rollback"
    preserve_work_root = False
    try:
        plan = validate_backup(Path(source), staging_root)
        _transform_staged_json(plan, transform_json)
        selected_components = (
            _COMPONENT_ORDER
            if not plan.legacy
            else tuple(
                component
                for component in _COMPONENT_ORDER
                if plan.components[component]
            )
        )
        live_started = False
        restored_files = 0
        before_state: dict[str, Any] = {}
        states: dict[str, str] = {}
        with persistence_maintenance(timeout=15.0):
            if safety_backup is not None:
                create_backup(
                    layout,
                    safety_backup,
                    application_version=application_version,
                    transform_json=transform_json,
                    virtual_settings=safety_virtual_settings,
                )
            rollback_root.mkdir(parents=True, exist_ok=True)
            states, before_state = _snapshot_components(
                layout,
                selected_components,
                rollback_root,
            )
            _invoke_failure(failure_injector, "before_live_modification")
            try:
                live_started = True
                restored_files = _apply_staged(
                    plan,
                    layout,
                    selected_components,
                    failure_injector,
                )
                _invoke_failure(failure_injector, "before_verification")
                _verify_restored(plan, layout, failure_injector)
                _invoke_failure(failure_injector, "after_verification")
            except Exception as restore_error:
                if not live_started:
                    raise
                try:
                    _rollback(
                        layout,
                        selected_components,
                        rollback_root,
                        states,
                    )
                    after_rollback = _logical_state(layout, selected_components)
                    if after_rollback != before_state:
                        raise BackupError(
                            "Rollback verification did not reproduce the original state."
                        )
                except Exception as rollback_error:
                    preserve_work_root = True
                    parent = (
                        Path(recovery_parent)
                        if recovery_parent is not None
                        else layout.data_root / "backups"
                    )
                    recovery_path = work_root
                    try:
                        parent.mkdir(parents=True, exist_ok=True)
                        durable_path = parent / (
                            "restore_recovery_"
                            + datetime.now().strftime("%Y%m%dT%H%M%S")
                            + "_"
                            + uuid.uuid4().hex[:8]
                        )
                        shutil.move(str(work_root), str(durable_path))
                        recovery_path = durable_path
                    except OSError:
                        # The system temp path is still intentionally retained.
                        pass
                    raise RestoreTransactionError(
                        "Restore failed and rollback also failed. Recovery files were "
                        f"preserved at {recovery_path}. Restore error: {restore_error}; "
                        f"rollback error: {rollback_error}",
                        rollback_performed=False,
                        recovery_path=recovery_path,
                    ) from rollback_error
                raise RestoreTransactionError(
                    f"Restore failed; the original state was restored and verified: {restore_error}",
                    rollback_performed=True,
                ) from restore_error

        return RestoreResult(
            legacy=plan.legacy,
            restored_files=restored_files,
            safety_backup=Path(safety_backup) if safety_backup is not None else None,
        )
    finally:
        if not preserve_work_root and work_root.exists():
            shutil.rmtree(work_root, ignore_errors=True)
