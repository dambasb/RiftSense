from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path


def _is_riftsense_entrypoint() -> bool:
    if getattr(sys, "frozen", False):
        return True
    main_module = sys.modules.get("__main__")
    main_file = str(getattr(main_module, "__file__", "") or "")
    return Path(main_file).name.lower() == "riftsense.py"


if _is_riftsense_entrypoint():
    from .updater import UpdateError, handle_update_cli

    try:
        handle_update_cli()
    except UpdateError as exc:
        if os.name == "nt":
            try:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    str(exc),
                    "RiftSense Update",
                    0x10,
                )
            except (AttributeError, OSError):
                pass
        raise SystemExit(1)

    from .update_runtime import install_mainloop_hook

    install_mainloop_hook()
