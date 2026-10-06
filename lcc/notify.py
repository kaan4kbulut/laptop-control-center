"""Mod değişince ekran göstergesi (OSD) ve Omarchy bar eklentisini yenileme.

Omarchy varsa onun OSD'si kullanılır; yoksa her masaüstünde çalışan notify-send yedeğidir.
"""

from __future__ import annotations

import shutil
import subprocess

from .i18n import t

BAR_TARGET = "laptop-control-center"
ICONS = {"performance": "󰓅", "balanced": "󰊚", "quiet": "󰖔", "powersave": "󰌪"}


def bar_refresh() -> None:
    """Bar eklentisi çalışıyorsa durumunu hemen yeniden okusun (beklemeden)."""
    if shutil.which("omarchy-shell"):
        subprocess.Popen(["omarchy-shell", "-q", BAR_TARGET, "refresh"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mode_changed(ctl, mode: str, fan: str | None) -> None:
    bar_refresh()
    title = t("bar.mode", mode=t("mode." + mode))
    if shutil.which("omarchy-osd"):
        subprocess.run(["omarchy-osd", "-i", ICONS.get(mode, ""), "-m", title, "-d", "1500"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return
    if not shutil.which("notify-send"):
        return
    body = t("mode.note." + mode)
    if fan:
        body += f" · {t('status.fan').lower()} {t('fan.' + fan).lower()}"
    subprocess.run([
        "notify-send", "-a", t("app.title"), "-i", "preferences-system-power",
        "-h", "string:x-canonical-private-synchronous:lcc-mode",
        "-h", "string:x-dunst-stack-tag:lcc-mode",
        "-t", "2000", title, body,
    ], check=False)
