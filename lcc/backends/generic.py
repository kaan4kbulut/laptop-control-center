"""Genel Linux arka ucu: power-profiles-daemon (mod) ve UPower (klavye parlaklığı).

Özel sürücüsü olmayan her dizüstünde root istemeden çalışır. Fan kontrolü yoktur.
"""

from __future__ import annotations

import glob

from gi.repository import GLib

from .. import dbus
from ..hardware import read, read_int
from .base import Backend, Capabilities, KeyboardCaps, KeyboardState, Unsupported

UPOWER = "org.freedesktop.UPower"
KBD_PATH = "/org/freedesktop/UPower/KbdBacklight"
KBD_IFACE = "org.freedesktop.UPower.KbdBacklight"

# Yeni sürümler UPower adını, eskiler net.hadess adını kullanır.
PPD_NAMES = [
    ("org.freedesktop.UPower.PowerProfiles", "/org/freedesktop/UPower/PowerProfiles"),
    ("net.hadess.PowerProfiles", "/net/hadess/PowerProfiles"),
]

TO_PPD = {"performance": "performance", "balanced": "balanced", "powersave": "power-saver"}
FROM_PPD = {v: k for k, v in TO_PPD.items()}


class GenericBackend(Backend):
    id = "generic"
    name = "Linux (power-profiles-daemon)"

    @classmethod
    def probe(cls) -> int:
        return 10

    def __init__(self):
        self._ppd = next(((n, p) for n, p in PPD_NAMES if dbus.has_name(n)), None)
        self._kbd_max = 0
        if dbus.has_name(UPOWER):
            try:
                self._kbd_max = int(dbus.call(UPOWER, KBD_PATH, KBD_IFACE, "GetMaxBrightness"))
            except GLib.Error:
                pass

    def _ppd_prop(self, prop):
        name, path = self._ppd
        return dbus.get_prop(name, path, name, prop)

    def capabilities(self) -> Capabilities:
        modes = []
        if self._ppd:
            try:
                avail = {p["Profile"] for p in self._ppd_prop("Profiles")}
                modes = [m for m, p in TO_PPD.items() if p in avail]
            except GLib.Error:
                pass
        kb = KeyboardCaps(brightness_max=self._kbd_max) if self._kbd_max else None
        bat = next(iter(glob.glob("/sys/class/power_supply/BAT*")), None)
        ends = []
        if bat and read(bat + "/charge_control_end_threshold") is not None:
            avail = read(bat + "/charge_control_end_available_thresholds")
            ends = [int(x) for x in avail.split()] if avail else [60, 70, 80, 90, 100]
        return Capabilities(modes=modes, fan_modes=[], keyboard=kb, charge_end=ends)

    def current(self):
        if not self._ppd:
            return None, None
        try:
            return FROM_PPD.get(self._ppd_prop("ActiveProfile")), None
        except GLib.Error:
            return None, None

    def apply(self, mode: str, fan: str) -> None:
        if not self._ppd or mode not in TO_PPD:
            raise Unsupported(mode)
        name, path = self._ppd
        dbus.set_prop(name, path, name, "ActiveProfile", GLib.Variant("s", TO_PPD[mode]))

    def keyboard(self) -> KeyboardState:
        if not self._kbd_max:
            raise Unsupported
        b = int(dbus.call(UPOWER, KBD_PATH, KBD_IFACE, "GetBrightness"))
        return KeyboardState(brightness=b)

    def set_keyboard(self, state: KeyboardState) -> None:
        if not self._kbd_max:
            raise Unsupported
        dbus.call(UPOWER, KBD_PATH, KBD_IFACE, "SetBrightness", "i",
                  max(0, min(self._kbd_max, int(state.brightness))))

    def charge_thresholds(self):
        bat = next(iter(glob.glob("/sys/class/power_supply/BAT*")), None)
        if not bat:
            return None, None
        return (read_int(bat + "/charge_control_start_threshold"),
                read_int(bat + "/charge_control_end_threshold"))
