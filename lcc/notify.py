"""Mod değişince masaüstü bildirimi. Asıl OSD penceresi arayüz aşamasında gelecek;
o yoksa bu, her masaüstünde çalışan notify-send yedeğidir."""

from __future__ import annotations

import shutil
import subprocess

from .i18n import t


def mode_changed(ctl, mode: str, fan: str | None) -> None:
    if not shutil.which("notify-send"):
        return
    body = t("mode.note." + mode)
    if fan:
        body += f" · {t('status.fan').lower()} {t('fan.' + fan).lower()}"
    subprocess.run([
        "notify-send", "-a", t("app.title"), "-i", "preferences-system-power",
        "-h", "string:x-canonical-private-synchronous:lcc-mode",
        "-h", "string:x-dunst-stack-tag:lcc-mode",
        "-t", "2000",
        f"{t('mode.' + mode)}", body,
    ], check=False)
