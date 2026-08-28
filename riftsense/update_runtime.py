from __future__ import annotations

import queue
import sys
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk

from .updater import (
    download_update_to_temp,
    fetch_available_update,
    launch_update_applier,
    update_install_supported,
)
from .version import UPDATE_VERSION


_AUTO_CHECK_INTERVAL_SECONDS = 6 * 60 * 60


def _main_module():
    return sys.modules.get("__main__")


def _settings():
    module = _main_module()
    value = getattr(module, "SETTINGS", None) if module is not None else None
    return value if isinstance(value, dict) else {}


def _save_settings():
    module = _main_module()
    saver = getattr(module, "save_settings", None) if module is not None else None
    if callable(saver):
        try:
            return bool(saver())
        except Exception:
            return False
    return False


def _log_warning(message):
    module = _main_module()
    logger = getattr(module, "log_warning", None) if module is not None else None
    if callable(logger):
        try:
            logger(str(message))
            return
        except Exception:
            return


def _set_status(app, text):
    app._riftsense_update_status_text = str(text or "")
    variable = getattr(app, "riftsense_update_status_var", None)
    if variable is not None:
        variable.set(app._riftsense_update_status_text)


def _ensure_watch(app):
    if getattr(app, "_riftsense_update_watch_job", None) is None:
        app._riftsense_update_watch_job = app.after(
            90,
            lambda: _watch_queue(app),
        )


def _check_for_updates(app, manual=True):
    if getattr(app, "_riftsense_update_check_inflight", False):
        if manual:
            _set_status(app, "Updates • check already running")
        return

    app._riftsense_update_check_inflight = True
    _set_status(
        app,
        f"Updates • checking GitHub Releases • current {UPDATE_VERSION}",
    )

    def worker():
        info = None
        error = None
        try:
            info = fetch_available_update(
                UPDATE_VERSION,
                user_agent=f"RiftSense/{UPDATE_VERSION}",
            )
        except Exception as exc:
            error = str(exc)
        app._riftsense_update_queue.put(("check", bool(manual), info, error))

    threading.Thread(
        target=worker,
        name="RiftSenseUpdateCheck",
        daemon=True,
    ).start()
    _ensure_watch(app)


def _start_download(app, info):
    if getattr(app, "_riftsense_update_download_inflight", False):
        return
    if not update_install_supported():
        app.rs_warning(
            "Updates",
            "Automatic installation is available only in the packaged RiftSense.exe build.",
        )
        return

    app._riftsense_update_download_inflight = True
    _set_status(
        app,
        f"Updates • downloading {info.version} from GitHub Releases",
    )

    def worker():
        path = None
        error = None
        try:
            path = download_update_to_temp(
                info,
                user_agent=f"RiftSense/{UPDATE_VERSION}",
            )
        except Exception as exc:
            error = str(exc)
        app._riftsense_update_queue.put(("download", info, path, error))

    threading.Thread(
        target=worker,
        name="RiftSenseUpdateDownload",
        daemon=True,
    ).start()
    _ensure_watch(app)


def _prompt_update(app, info):
    notes = str(getattr(info, "body", "") or "").strip()
    if len(notes) > 2200:
        notes = notes[:2200].rstrip() + "\n…"
    if not notes:
        notes = "See the GitHub Release for the full change list."

    install_supported = update_install_supported()
    action_text = "Update now" if install_supported else "Open release"
    message = (
        f"RiftSense {info.version} is available.\n"
        f"Current version: {UPDATE_VERSION}\n\n"
        f"WHAT'S NEW\n{notes}\n\n"
        + (
            "Update now downloads one new RiftSense.exe, verifies its SHA-256 "
            "checksum, replaces the old EXE after RiftSense closes, and restarts automatically."
            if install_supported
            else "Automatic installation is enabled only in the packaged RiftSense.exe build."
        )
    )
    accepted = app.riftsense_dialog(
        "RiftSense update available",
        message,
        kind="info",
        confirm=True,
        confirm_text=action_text,
        cancel_text="Later",
        width=690,
        height=520,
        scrollable=True,
        resizable=True,
    )
    if not accepted:
        return
    if not install_supported:
        if getattr(info, "html_url", ""):
            webbrowser.open(info.html_url)
        return
    _start_download(app, info)


def _watch_queue(app):
    app._riftsense_update_watch_job = None
    while True:
        try:
            event = app._riftsense_update_queue.get_nowait()
        except queue.Empty:
            break

        if event[0] == "check":
            _kind, manual, info, error = event
            app._riftsense_update_check_inflight = False
            settings = _settings()
            settings["last_update_check_epoch"] = int(time.time())
            _save_settings()

            if error:
                _set_status(app, f"Updates • check failed • {error}")
                _log_warning("Update check failed: " + str(error))
                if manual:
                    app.rs_error(
                        "Update check",
                        f"RiftSense could not check GitHub Releases.\n\n{error}",
                    )
                continue

            if info is None:
                _set_status(app, f"Updates • up to date • {UPDATE_VERSION}")
                if manual:
                    app.rs_success(
                        "RiftSense is up to date",
                        f"You are running the latest available version: {UPDATE_VERSION}",
                    )
                continue

            _set_status(
                app,
                f"Updates • {info.version} available • current {UPDATE_VERSION}",
            )
            _prompt_update(app, info)
            continue

        if event[0] == "download":
            _kind, info, path, error = event
            app._riftsense_update_download_inflight = False
            if error:
                _set_status(app, f"Updates • download failed • {error}")
                app.rs_error(
                    "Update failed",
                    (
                        "RiftSense downloaded no replacement and your current version "
                        f"was left untouched.\n\n{error}"
                    ),
                )
                continue

            _set_status(
                app,
                f"Updates • {info.version} verified • restarting RiftSense",
            )
            try:
                launch_update_applier(path)
            except Exception as exc:
                app.rs_error(
                    "Update failed",
                    (
                        "The new RiftSense.exe was downloaded and verified, but the "
                        f"restart/update step could not start.\n\n{exc}"
                    ),
                )
                continue

            closer = getattr(app, "on_close", None)
            if callable(closer):
                closer()
            else:
                app.destroy()
            return

    if (
        getattr(app, "_riftsense_update_check_inflight", False)
        or getattr(app, "_riftsense_update_download_inflight", False)
        or not app._riftsense_update_queue.empty()
    ):
        _ensure_watch(app)


def _maybe_auto_check(app):
    settings = _settings()
    if not bool(settings.get("auto_check_updates", True)):
        _set_status(
            app,
            f"Updates • automatic checks off • current {UPDATE_VERSION}",
        )
        return

    if not update_install_supported():
        _set_status(
            app,
            f"Updates • current {UPDATE_VERSION} • auto-install activates in RiftSense.exe",
        )
        return

    try:
        last_check = float(settings.get("last_update_check_epoch", 0) or 0)
    except (TypeError, ValueError):
        last_check = 0.0
    if time.time() - last_check < _AUTO_CHECK_INTERVAL_SECONDS:
        return
    _check_for_updates(app, manual=False)


def attach_update_runtime(app):
    if getattr(app, "_riftsense_update_runtime_attached", False):
        return
    if not hasattr(app, "settings_general_tab") or not hasattr(app, "riftsense_dialog"):
        return

    app._riftsense_update_runtime_attached = True
    app._riftsense_update_queue = queue.Queue()
    app._riftsense_update_check_inflight = False
    app._riftsense_update_download_inflight = False
    app._riftsense_update_watch_job = None

    settings = _settings()
    settings.setdefault("auto_check_updates", True)
    settings.setdefault("last_update_check_epoch", 0)

    panel = ttk.LabelFrame(
        app.settings_general_tab,
        text="UPDATES",
    )
    panel.pack(
        fill="x",
        pady=(0, 7),
    )

    body = ttk.Frame(
        panel,
        style="Panel.TFrame",
    )
    body.pack(
        fill="x",
        padx=8,
        pady=7,
    )

    top = ttk.Frame(
        body,
        style="Panel.TFrame",
    )
    top.pack(fill="x")

    app.riftsense_auto_updates_var = tk.BooleanVar(
        value=bool(settings.get("auto_check_updates", True))
    )

    def on_toggle():
        settings["auto_check_updates"] = bool(app.riftsense_auto_updates_var.get())
        _save_settings()
        if settings["auto_check_updates"]:
            _set_status(app, f"Updates • automatic checks on • current {UPDATE_VERSION}")
            app.after(250, lambda: _maybe_auto_check(app))
        else:
            _set_status(app, f"Updates • automatic checks off • current {UPDATE_VERSION}")

    ttk.Checkbutton(
        top,
        text="Automatically check GitHub Releases for RiftSense updates",
        variable=app.riftsense_auto_updates_var,
        command=on_toggle,
    ).pack(side="left")

    ttk.Button(
        top,
        text="Check for updates",
        style="Ghost.TButton",
        command=lambda: _check_for_updates(app, manual=True),
    ).pack(side="right")

    app.riftsense_update_status_var = tk.StringVar(
        value=f"Updates • current {UPDATE_VERSION}"
    )
    ttk.Label(
        body,
        textvariable=app.riftsense_update_status_var,
        style="Accent.Panel.TLabel",
        wraplength=1080,
        justify="left",
    ).pack(
        anchor="w",
        pady=(7, 2),
    )

    ttk.Label(
        body,
        text=(
            "EXE builds use one RiftSense.exe only. Update now downloads the new EXE "
            "to a temporary location, verifies its published SHA-256 checksum, replaces "
            "the old EXE after shutdown, restarts RiftSense, and removes the temporary copy."
        ),
        style="Muted.Panel.TLabel",
        wraplength=1080,
        justify="left",
    ).pack(anchor="w")

    app.after(5000, lambda: _maybe_auto_check(app))


def install_mainloop_hook():
    original = tk.Tk.mainloop
    if getattr(original, "_riftsense_update_hook", False):
        return

    def wrapped_mainloop(self, n=0):
        try:
            attach_update_runtime(self)
        except Exception as exc:
            _log_warning("Update UI initialization failed: " + str(exc))
        return original(self, n)

    wrapped_mainloop._riftsense_update_hook = True
    tk.Tk.mainloop = wrapped_mainloop
