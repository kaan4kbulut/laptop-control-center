"""Gio üzerinden küçük, eşzamanlı DBus yardımcıları."""

from __future__ import annotations

from gi.repository import Gio, GLib

_buses: dict[str, Gio.DBusConnection] = {}


def bus(kind: str = "system") -> Gio.DBusConnection:
    if kind not in _buses:
        t = Gio.BusType.SYSTEM if kind == "system" else Gio.BusType.SESSION
        _buses[kind] = Gio.bus_get_sync(t, None)
    return _buses[kind]


def call(name: str, path: str, iface: str, method: str,
         sig: str | None = None, *args, kind: str = "system", timeout: int = 5000):
    """Bir DBus metodunu çağırır; tek dönüş değerini açar."""
    params = GLib.Variant(f"({sig})", args) if sig else None
    res = bus(kind).call_sync(name, path, iface, method, params, None,
                              Gio.DBusCallFlags.NONE, timeout, None)
    out = res.unpack() if res is not None else ()
    return out[0] if len(out) == 1 else out


def get_prop(name: str, path: str, iface: str, prop: str, kind: str = "system"):
    return call(name, path, "org.freedesktop.DBus.Properties", "Get",
                "ss", iface, prop, kind=kind)


def set_prop(name: str, path: str, iface: str, prop: str, value: GLib.Variant,
             kind: str = "system"):
    params = GLib.Variant("(ssv)", (iface, prop, value))
    bus(kind).call_sync(name, path, "org.freedesktop.DBus.Properties", "Set",
                        params, None, Gio.DBusCallFlags.NONE, 5000, None)


def has_name(name: str, kind: str = "system") -> bool:
    try:
        return bool(call("org.freedesktop.DBus", "/org/freedesktop/DBus",
                         "org.freedesktop.DBus", "NameHasOwner", "s", name, kind=kind))
    except GLib.Error:
        return False
