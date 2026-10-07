"""Sistemin güç profiliyle (power-profiles-daemon) eşitleme.

Omarchy'nin menüsü ve güç paneli power-profiles-daemon'un profilini değiştirir ve
seçimi güç kaynağına göre hatırlar (~/.local/state/omarchy/powerprofiles/{ac,battery}).
Kontrol merkezi mod değiştirince ikisini de günceller; sistemden profil değişince
servis (lcc daemon) karşılık gelen modu uygular. Böylece iki taraf aynı modu gösterir
ve fiş takılıp çekilince birbirinin seçimini ezmez.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from gi.repository import GLib

from . import dbus

log = logging.getLogger("lcc.profiles")

# Yeni sürümler UPower adını, eskiler net.hadess adını kullanır.
PPD_NAMES = [
    ("org.freedesktop.UPower.PowerProfiles", "/org/freedesktop/UPower/PowerProfiles"),
    ("net.hadess.PowerProfiles", "/net/hadess/PowerProfiles"),
]
TO_PPD = {"performance": "performance", "balanced": "balanced",
          "quiet": "power-saver", "powersave": "power-saver"}


def ppd() -> tuple[str, str] | None:
    return next(((n, p) for n, p in PPD_NAMES if dbus.has_name(n)), None)


def active() -> str | None:
    d = ppd()
    if not d:
        return None
    try:
        return dbus.get_prop(d[0], d[1], d[0], "ActiveProfile")
    except GLib.Error:
        return None


def mode_for(profile: str, modes: list[str], on_battery: bool) -> str | None:
    """Sistem profiline karşılık gelen mod. Güç tasarrufu pilde Pil Tasarrufu, prizde Sessiz."""
    if profile == "power-saver":
        order = ("powersave", "quiet") if on_battery else ("quiet", "powersave")
        return next((m for m in order if m in modes), None)
    return profile if profile in modes else None


def _omarchy_state(source: str) -> Path | None:
    if not shutil.which("omarchy-powerprofiles-set"):
        return None
    base = os.environ.get("OMARCHY_POWERPROFILES_STATE_DIR") or os.path.join(
        os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state"),
        "omarchy", "powerprofiles")
    return Path(base) / source


def remember(source: str, mode: str) -> None:
    """Omarchy'nin o güç kaynağı için hatırladığı profili bu moda eşitle."""
    profile, f = TO_PPD.get(mode), _omarchy_state(source)
    if not profile or not f:
        return
    try:
        if f.read_text().strip() == profile:
            return
    except OSError:
        pass
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(profile + "\n")
    except OSError as e:
        log.warning("omarchy power profile state: %s", e)


def sync(source: str, mode: str, current: bool = True) -> None:
    """Modu sistem profiline yansıtır. current: bu kaynak şu an etkin, profili de değiştir."""
    remember(source, mode)
    profile, d = TO_PPD.get(mode), ppd()
    if not current or not profile or not d or active() == profile:
        return
    try:
        dbus.set_prop(d[0], d[1], d[0], "ActiveProfile", GLib.Variant("s", profile))
    except GLib.Error as e:
        log.warning("power profile %s: %s", profile, e.message)
