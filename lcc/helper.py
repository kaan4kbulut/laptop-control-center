"""Root yardımcısı (/usr/local/libexec/lcc-helper) çağrıları.

pkexec ile çalışır; polkit kuralı wheel grubuna parolasız izin verir (data/polkit/).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess

log = logging.getLogger("lcc.helper")
PATH = "/usr/local/libexec/lcc-helper"
MIN_VERSION = 2


def installed() -> bool:
    return os.access(PATH, os.X_OK) and shutil.which("pkexec") is not None


def version() -> int:
    """Kurulu yardımcının sürümü; okunamazsa 0 (sürüm komutu root gerektirmez ama pkexec ister)."""
    try:
        with open(PATH) as f:
            for line in f:
                if line.startswith("VERSION="):
                    return int(line.split("=", 1)[1])
    except (OSError, ValueError):
        pass
    return 0


def run(*args: str, timeout: float = 30) -> bool:
    try:
        r = subprocess.run(["pkexec", PATH, *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("lcc-helper %s: %s", args[0] if args else "", e)
        return False
    if r.returncode != 0:
        log.warning("lcc-helper %s failed (%s): %s", " ".join(args), r.returncode, r.stderr.strip())
        return False
    return True
