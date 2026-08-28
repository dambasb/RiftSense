from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from functools import cmp_to_key
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


REPOSITORY = "dambasb/RiftSense"
RELEASES_API_URL = f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=20"
RELEASE_ASSET_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"
EXE_ASSET_NAME = "RiftSense.exe"
CHECKSUM_ASSET_NAME = "RiftSense.exe.sha256"


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    tag: str
    title: str
    body: str
    html_url: str
    exe_url: str
    checksum_url: str


def _parse_semver(value: str):
    text = str(value or "").strip()
    if text.lower().startswith("v"):
        text = text[1:]
    match = re.fullmatch(
        r"(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?",
        text,
    )
    if not match:
        return None
    major, minor, patch = (int(match.group(i)) for i in range(1, 4))
    prerelease = match.group(4)
    tokens = []
    if prerelease:
        for token in prerelease.split("."):
            tokens.append(int(token) if token.isdigit() else token.lower())
    return (major, minor, patch, tuple(tokens))


def _compare_prerelease(left, right):
    if not left and not right:
        return 0
    if not left:
        return 1
    if not right:
        return -1

    for left_token, right_token in zip(left, right):
        if left_token == right_token:
            continue
        left_is_int = isinstance(left_token, int)
        right_is_int = isinstance(right_token, int)
        if left_is_int and right_is_int:
            return 1 if left_token > right_token else -1
        if left_is_int != right_is_int:
            # SemVer: numeric identifiers have lower precedence than non-numeric.
            return -1 if left_is_int else 1
        return 1 if str(left_token) > str(right_token) else -1

    if len(left) == len(right):
        return 0
    return 1 if len(left) > len(right) else -1


def compare_versions(left: str, right: str) -> int:
    """Return -1/0/1 for semantic-version comparison."""
    left_parsed = _parse_semver(left)
    right_parsed = _parse_semver(right)
    if left_parsed is None or right_parsed is None:
        raise ValueError(f"Invalid semantic version: {left!r} or {right!r}")

    left_base = left_parsed[:3]
    right_base = right_parsed[:3]
    if left_base != right_base:
        return 1 if left_base > right_base else -1
    return _compare_prerelease(left_parsed[3], right_parsed[3])


def is_newer_version(candidate: str, current: str) -> bool:
    try:
        return compare_versions(candidate, current) > 0
    except ValueError:
        return False


def _asset_url(asset) -> str:
    if not isinstance(asset, dict):
        return ""
    return str(asset.get("browser_download_url") or "").strip()


def _validate_release_asset_url(url: str) -> str:
    text = str(url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        raise UpdateError("Update asset URL is not a trusted GitHub HTTPS URL.")
    if not text.startswith(RELEASE_ASSET_PREFIX):
        raise UpdateError("Update asset is outside the RiftSense GitHub Releases path.")
    return text


def select_update_from_releases(releases, current_version: str) -> UpdateInfo | None:
    if not isinstance(releases, list):
        raise UpdateError("GitHub returned an unexpected releases payload.")

    candidates = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "").strip()
        parsed = _parse_semver(tag)
        if parsed is None or not is_newer_version(tag, current_version):
            continue

        assets = release.get("assets") or []
        by_name = {
            str(asset.get("name") or ""): asset
            for asset in assets
            if isinstance(asset, dict)
        }
        exe_url = _asset_url(by_name.get(EXE_ASSET_NAME))
        checksum_url = _asset_url(by_name.get(CHECKSUM_ASSET_NAME))
        if not exe_url or not checksum_url:
            continue

        candidates.append(
            (
                parsed,
                UpdateInfo(
                    version=tag[1:] if tag.lower().startswith("v") else tag,
                    tag=tag,
                    title=str(release.get("name") or tag),
                    body=str(release.get("body") or ""),
                    html_url=str(release.get("html_url") or ""),
                    exe_url=_validate_release_asset_url(exe_url),
                    checksum_url=_validate_release_asset_url(checksum_url),
                ),
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=cmp_to_key(
            lambda left, right: compare_versions(
                left[1].version,
                right[1].version,
            )
        ),
        reverse=True,
    )
    return candidates[0][1]


def fetch_available_update(
    current_version: str,
    *,
    user_agent: str = "RiftSense",
    timeout: float = 8.0,
) -> UpdateInfo | None:
    request = Request(
        RELEASES_API_URL,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(2_000_000)
    except Exception as exc:
        raise UpdateError(f"Could not check GitHub Releases: {exc}") from exc

    try:
        releases = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise UpdateError("GitHub returned invalid release metadata.") from exc

    return select_update_from_releases(releases, current_version)


def parse_sha256_text(text: str) -> str:
    match = re.search(r"\b([0-9a-fA-F]{64})\b", str(text or ""))
    if not match:
        raise UpdateError("Release checksum file does not contain a SHA-256 hash.")
    return match.group(1).lower()


def _read_small_text(url: str, *, user_agent: str, timeout: float) -> str:
    request = Request(
        _validate_release_asset_url(url),
        headers={"User-Agent": user_agent, "Accept": "text/plain"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read(32_768)
    except Exception as exc:
        raise UpdateError(f"Could not download update checksum: {exc}") from exc
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise UpdateError("Update checksum was not valid UTF-8 text.") from exc


def download_update_to_temp(
    info: UpdateInfo,
    *,
    user_agent: str = "RiftSense",
    timeout: float = 30.0,
) -> Path:
    expected_hash = parse_sha256_text(
        _read_small_text(
            info.checksum_url,
            user_agent=user_agent,
            timeout=timeout,
        )
    )

    destination = Path(tempfile.gettempdir()) / (
        f"RiftSense-update-{info.version}-{int(time.time())}.exe"
    )
    part_path = destination.with_suffix(destination.suffix + ".part")

    request = Request(
        _validate_release_asset_url(info.exe_url),
        headers={
            "User-Agent": user_agent,
            "Accept": "application/octet-stream",
        },
    )
    digest = hashlib.sha256()
    try:
        with urlopen(request, timeout=timeout) as response, part_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                output.write(chunk)
    except Exception as exc:
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise UpdateError(f"Could not download RiftSense update: {exc}") from exc

    actual_hash = digest.hexdigest().lower()
    if actual_hash != expected_hash:
        try:
            part_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise UpdateError(
            "Downloaded RiftSense.exe failed SHA-256 verification. "
            "The update was not installed."
        )

    try:
        os.replace(part_path, destination)
    except OSError as exc:
        raise UpdateError(f"Could not finalize downloaded update: {exc}") from exc
    return destination


def update_install_supported() -> bool:
    return bool(
        os.name == "nt"
        and getattr(sys, "frozen", False)
        and Path(sys.executable).suffix.lower() == ".exe"
    )


def launch_update_applier(downloaded_exe: Path, *, target_exe: Path | None = None) -> None:
    if not update_install_supported():
        raise UpdateError("Automatic install is available only in the packaged RiftSense.exe build.")

    downloaded_exe = Path(downloaded_exe).resolve()
    target_exe = Path(target_exe or sys.executable).resolve()
    if not downloaded_exe.is_file():
        raise UpdateError("Downloaded RiftSense.exe no longer exists.")

    try:
        subprocess.Popen(
            [
                str(downloaded_exe),
                "--riftsense-apply-update",
                str(target_exe),
                str(os.getpid()),
            ],
            close_fds=True,
        )
    except OSError as exc:
        raise UpdateError(f"Could not start the RiftSense update process: {exc}") from exc


def _wait_for_process_exit(pid: int, timeout_seconds: float = 90.0) -> None:
    if os.name == "nt":
        try:
            import ctypes

            SYNCHRONIZE = 0x00100000
            WAIT_TIMEOUT = 0x00000102
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
            if handle:
                try:
                    result = kernel32.WaitForSingleObject(
                        handle,
                        int(max(1.0, timeout_seconds) * 1000),
                    )
                    if result == WAIT_TIMEOUT:
                        raise UpdateError("Timed out waiting for the old RiftSense process to close.")
                    return
                finally:
                    kernel32.CloseHandle(handle)
        except UpdateError:
            raise
        except Exception:
            pass

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(int(pid), 0)
        except OSError:
            return
        time.sleep(0.25)
    raise UpdateError("Timed out waiting for the old RiftSense process to close.")


def _replace_target_from_running_copy(target_exe: Path) -> None:
    source_exe = Path(sys.executable).resolve()
    target_exe = Path(target_exe).resolve()
    target_exe.parent.mkdir(parents=True, exist_ok=True)
    staged_target = target_exe.with_name(target_exe.name + ".new")

    last_error = None
    for _ in range(40):
        try:
            shutil.copy2(source_exe, staged_target)
            os.replace(staged_target, target_exe)
            return
        except OSError as exc:
            last_error = exc
            try:
                staged_target.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.25)
    raise UpdateError(f"Could not replace the old RiftSense.exe: {last_error}")


def _schedule_temp_cleanup(path: Path) -> None:
    cleanup_path = Path(path)

    def worker():
        time.sleep(1.5)
        for _ in range(30):
            try:
                cleanup_path.unlink(missing_ok=True)
                return
            except OSError:
                time.sleep(0.4)

    threading.Thread(
        target=worker,
        name="RiftSenseUpdateCleanup",
        daemon=True,
    ).start()


def handle_update_cli(argv=None) -> bool:
    """Handle the temporary self-update modes before Tk is created.

    Returns True only when a cleanup argument was consumed and normal startup
    should continue. The apply-update path exits the process after relaunching
    the installed executable.
    """
    args = list(sys.argv if argv is None else argv)

    if "--riftsense-apply-update" in args:
        index = args.index("--riftsense-apply-update")
        try:
            target_exe = Path(args[index + 1]).resolve()
            old_pid = int(args[index + 2])
        except (IndexError, TypeError, ValueError) as exc:
            raise UpdateError("RiftSense update arguments were invalid.") from exc

        _wait_for_process_exit(old_pid)
        _replace_target_from_running_copy(target_exe)
        source_temp_exe = Path(sys.executable).resolve()
        subprocess.Popen(
            [
                str(target_exe),
                "--riftsense-cleanup-update",
                str(source_temp_exe),
            ],
            close_fds=True,
        )
        raise SystemExit(0)

    if "--riftsense-cleanup-update" in args:
        index = args.index("--riftsense-cleanup-update")
        try:
            cleanup_path = Path(args[index + 1]).resolve()
        except IndexError as exc:
            raise UpdateError("RiftSense cleanup arguments were invalid.") from exc
        _schedule_temp_cleanup(cleanup_path)
        # Prevent application code from seeing updater-only CLI parameters.
        if argv is None:
            del sys.argv[index : index + 2]
        return True

    return False
