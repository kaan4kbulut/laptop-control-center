"""Kullanıcı servisi: girişte ve fiş takılıp çekilince seçili modu yeniden uygular,
pil tasarrufu kademesini (lcc/power.py) yönetir.

tccd güç kaynağı değişince geçici profili sıfırlar ve kendi ayarındaki profile döner;
bu değişikliği birkaç saniye içinde yapar. Bu yüzden değişiklikten sonra birkaç kez
kontrol edip gerekirse kullanıcının seçimini yeniden uygularız.
"""

from __future__ import annotations

import logging
import os
import signal

from gi.repository import Gio, GLib

from . import camera, config, dbus, notify, power
from . import hardware as hw
from .backends.base import SetupRequired, Unsupported
from .controller import Controller

log = logging.getLogger("lcc.daemon")
CHECK_DELAYS = (2, 5, 10, 20)   # saniye


class Daemon:
    def __init__(self):
        self.ctl = Controller()
        self.loop = GLib.MainLoop()
        self._gen = 0
        self.power = power.PowerManager(self.ctl.backend)
        self._eval_pending = 0
        self._monitors = []

    def _check(self) -> bool:
        try:
            if self.ctl.reapply():
                log.info("reapplied %s for %s", self.ctl.desired(), self.ctl.source())
                notify.bar_refresh()
        except (SetupRequired, Unsupported) as e:
            log.warning("cannot apply: %s", e)
        except GLib.Error as e:
            log.warning("backend error: %s", e.message)
        return False

    def schedule_checks(self) -> None:
        # Önceki değişiklikten kalan kontroller kuşak numarasıyla geçersiz kılınır.
        self._gen += 1
        gen = self._gen
        for d in CHECK_DELAYS:
            GLib.timeout_add_seconds(d, lambda: gen == self._gen and self._check())

    def _on_upower(self, _conn, _sender, _path, _iface, _signal, params):
        _, changed, _ = params.unpack()
        if "OnBattery" in changed:
            log.info("power source changed: on_battery=%s", changed["OnBattery"])
            self.schedule_checks()
            self._power(lambda: self.power.on_power_source_changed(bool(changed["OnBattery"])))

    # --- pil tasarrufu ----------------------------------------------------------
    def _power(self, fn) -> None:
        level = self.power.level
        try:
            fn()
        except Exception:
            log.exception("power saving failed")
        if self.power.level != level:
            notify.bar_refresh()

    def _evaluate_soon(self) -> None:
        """Dosya değişiklikleri art arda gelir; 300 ms bekleyip bir kez değerlendir."""
        if self._eval_pending:
            GLib.source_remove(self._eval_pending)

        def run():
            self._eval_pending = 0
            self._power(lambda: self.power.evaluate(hw.on_battery()))
            return False
        self._eval_pending = GLib.timeout_add(300, run)

    def _watch(self, path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        mon = Gio.File.new_for_path(str(path.parent)).monitor_directory(Gio.FileMonitorFlags.WATCH_MOVES, None)
        name = path.name

        def changed(_m, f, other, _ev):
            if name in (f.get_basename(), other.get_basename() if other else None):
                self._evaluate_soon()
        mon.connect("changed", changed)
        self._monitors.append(mon)

    def _watch_hyprland(self) -> None:
        """Ölçek/ayar değişince Hyprland ekranı en yüksek tazelemeye döndürür; olayı
        yakalayıp 60 Hz'i hemen geri uygula ki ekran iki kez kararmasın."""
        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        run = os.environ.get("XDG_RUNTIME_DIR")
        if not sig or not run:
            return
        sock = f"{run}/hypr/{sig}/.socket2.sock"
        try:
            conn = Gio.SocketClient().connect(Gio.UnixSocketAddress.new(sock), None)
        except GLib.Error as e:
            log.warning("hyprland events: %s", e.message)
            return
        stream = Gio.DataInputStream.new(conn.get_input_stream())
        self._hypr = conn

        def on_line(src, res):
            try:
                line, _ = src.read_line_finish_utf8(res)
            except GLib.Error:
                return
            if line is None:
                return
            if line.startswith(("configreloaded", "monitoradded")):
                self._power(self.power.ensure_refresh)
            src.read_line_async(GLib.PRIORITY_DEFAULT, None, on_line)
        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, on_line)

    def run(self) -> None:
        dbus.bus("system").signal_subscribe(
            "org.freedesktop.UPower", "org.freedesktop.DBus.Properties", "PropertiesChanged",
            "/org/freedesktop/UPower", None, Gio.DBusSignalFlags.NONE, self._on_upower)
        for sig in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self._quit)
        log.info("backend: %s", self.ctl.backend.name)
        self._watch(power.REQUEST_FILE)
        self._watch(config.path())
        self._watch_hyprland()
        self._power(lambda: self.power.evaluate(hw.on_battery()))
        self._apply_camera()
        self._check()
        self.schedule_checks()
        self.loop.run()

    def _apply_camera(self) -> None:
        """Kullanıcı kamerayı kapattıysa yeniden başlatmadan sonra da kapalı kalsın."""
        if config.load().get("camera", True) is False and camera.enabled() and camera.available():
            log.info("camera disabled by preference")
            camera.set_enabled(False)

    def _quit(self) -> bool:
        self.loop.quit()
        return False


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    Daemon().run()
