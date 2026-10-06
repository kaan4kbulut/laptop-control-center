"""QML ile çekirdek arasındaki köprü.

Ölçüm ve komutlar ayrı bir iş parçacığında çalışır; DBus veya alt süreç beklerken
arayüz donmaz. QML üç harita görür: `info` (değişmez donanım bilgisi), `live`
(saniyede bir: sensörler, mod, fan) ve `desk` (iki saniyede bir: klavye, şarj,
masaüstü anahtarları).
"""

from __future__ import annotations

import logging
import time
import traceback

from PySide6.QtCore import Property, QObject, QThread, QTimer, Signal, Slot

from .. import camera, config, desktop, notify, power
from .. import hardware as hw
from ..backends.base import KeyboardState, Unsupported
from ..i18n import LANG, strings

log = logging.getLogger("lcc.gui")

LIVE_MS = 1000
DESK_EVERY = 2      # her kaç canlı ölçümde bir masaüstü durumunu oku


class Worker(QObject):
    liveReady = Signal(dict)
    deskReady = Signal(dict)
    infoReady = Signal(dict)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.ctl = None
        self.sensors = None
        self._tick = 0
        self.timer = None

    @Slot()
    def start(self):
        from ..controller import Controller
        from ..sensors import Sensors
        self.ctl = Controller()
        self.sensors = Sensors()
        self.ctl.backend.start_monitoring()
        self.sensors.sample()
        self.infoReady.emit(self._info())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll)
        self.timer.start(LIVE_MS)
        self._poll(force_desk=True)

    @Slot()
    def stop(self):
        if self.timer:
            self.timer.stop()
        if self.ctl:
            self.ctl.backend.stop_monitoring()

    def _info(self) -> dict:
        caps = self.ctl.caps
        b = self.ctl.backend
        gpu = hw.discrete_gpu()
        snap = self.sensors.sample()
        kbd = caps.keyboard
        return {
            "device": hw.dmi().pretty,
            "backend": b.name,
            "cpuName": snap.cpu_name,
            "gpuName": snap.gpu.name if snap.gpu else (gpu.name if gpu else ""),
            "modes": list(caps.modes),
            "fanModes": list(caps.fan_modes),
            "kbdMax": kbd.brightness_max if kbd else 0,
            "kbdColor": bool(kbd and kbd.color),
            "chargeEnd": list(caps.charge_end),
            "fnLock": caps.fn_lock,
            "needsSetup": b.needs_setup(),
            "camera": camera.available(),
            "fanCurves": dict(b.auto_curves(), custom=config.load()["custom_fan_curve"])
                         if hasattr(b, "auto_curves") and "custom" in caps.fan_modes else None,
            "lang": LANG,
        }

    def _poll(self, force_desk: bool = False):
        try:
            self.liveReady.emit(self._live())
            self._tick += 1
            if force_desk or self._tick % DESK_EVERY == 0:
                self.deskReady.emit(self._desk())
        except Exception as e:      # ölçüm hatası pencereyi düşürmesin
            log.warning("poll failed: %s", e)

    def _live(self) -> dict:
        s = self.sensors.sample()
        b = self.ctl.backend
        mode, fan = b.current()
        g = s.gpu
        return {
            "cpuFreq": s.cpu_freq, "cpuTemp": s.cpu_temp, "cpuUsage": s.cpu_usage,
            "pl1": s.cpu_power_limit, "pl2": s.cpu_power_limit2,
            "gpuSleeping": bool(g and g.sleeping), "gpuUsage": g.usage if g else None,
            "gpuTemp": g.temp if g else None, "gpuPower": g.power if g else None,
            "gpuPowerLimit": g.power_limit if g else None,
            "mem": s.mem_used, "memTotal": s.mem_total_gb,
            "disk": s.disk_used, "diskTotal": s.disk_total_gb,
            "onBattery": s.on_battery, "battery": s.battery, "batteryPower": s.battery_power,
            "fans": b.fan_speeds(),
            "batteryHours": hw.battery_hours(s.battery_power) if s.on_battery else None,
            "mode": mode, "fan": fan,
            "time": time.time(),
        }

    def _desk(self) -> dict:
        b = self.ctl.backend
        out = {
            "touchpad": desktop.touchpad(), "mic": desktop.mic_on(),
            "volume": desktop.volume(), "brightness": desktop.brightness(),
            "night": desktop.night_light(), "airplane": desktop.airplane(),
            "numlock": desktop.num_lock(), "capslock": desktop.caps_lock(),
            "camera": camera.enabled(),
            "fnlock": None, "chargeEnd": None, "chargeStart": None,
            "kbdBrightness": None, "kbdColorValue": None,
        }
        if self.ctl.caps.fn_lock:
            try:
                out["fnlock"] = b.fn_lock()
            except Exception:
                pass
        out["chargeStart"], out["chargeEnd"] = b.charge_thresholds()
        out["power"] = dict(power.status(), settings=power.settings(),
                            available=power.available(b), helper=power.helper_installed())
        try:
            k = b.keyboard()
            out["kbdBrightness"], out["kbdColorValue"] = k.brightness, k.color
        except Exception:
            pass
        return out

    # --- komutlar (QML'den kuyrukla gelir) --------------------------------------
    @Slot(str, "QVariantList")
    def run(self, action: str, args: list):
        try:
            getattr(self, "do_" + action)(*args)
        except Unsupported as e:
            self.failed.emit(str(e) or action)
        except Exception as e:
            log.warning("%s failed: %s", action, traceback.format_exc())
            self.failed.emit(f"{action}: {e}")
        if action in ("mode", "fan", "keyboard") or action.startswith("power"):
            notify.bar_refresh()
        self._poll(force_desk=True)

    def do_mode(self, mode):
        self.ctl.set_mode(mode)

    def do_fan(self, fan):
        self.ctl.set_fan(fan)

    def do_keyboard(self, color, brightness):
        b = self.ctl.backend
        cur = b.keyboard()
        state = KeyboardState(brightness=cur.brightness if brightness < 0 else int(brightness),
                              color=color or cur.color)
        b.set_keyboard(state)
        config.update(keyboard={"color": state.color, "brightness": state.brightness})

    def do_chargeEnd(self, value):
        self.ctl.backend.set_charge_end(int(value))

    def do_fnlock(self, on):
        self.ctl.backend.set_fn_lock(bool(on))

    def do_touchpad(self, on):
        desktop.set_touchpad(bool(on))

    def do_mic(self, on):
        desktop.set_mic(bool(on))

    def do_volume(self, v):
        desktop.set_volume(int(v))

    def do_brightness(self, v):
        desktop.set_brightness(int(v))

    def do_night(self, v):
        desktop.set_night_light(int(v))

    def do_powerLevel(self, level):
        power.request(level)

    def do_powerAuto(self, on):
        config.update(power_saving={"auto": bool(on)})

    def do_powerFeature(self, level, feature, on):
        cur = list(power.settings().get(level, []))
        if on and feature not in cur:
            cur.append(feature)
        elif not on and feature in cur:
            cur.remove(feature)
        config.update(power_saving={level: [f for f in power.FEATURES if f in cur]})

    def do_powerCap(self, level, value):
        caps = dict(power.settings().get("brightness_cap", {}))
        caps[level] = max(5, min(100, int(value)))
        config.update(power_saving={"brightness_cap": caps})

    def do_camera(self, on):
        if not camera.set_enabled(bool(on)):
            raise RuntimeError("camera")
        config.update(camera=bool(on))

    def do_fanCurve(self, points):
        """Özel fan eğrisini kaydeder, tccd profillerini yeniden yazar ve fanı Özel'e alır."""
        pts = [[int(t), max(0, min(100, int(round(v))))] for t, v in points]
        config.update(custom_fan_curve=pts)
        self.ctl.backend.setup(pts)
        mode, _ = self.ctl.desired()
        self.ctl.set_fan("custom")
        self.ctl.backend.apply(mode, "custom", force=True)
        self.infoReady.emit(self._info())

    def do_airplane(self, on):
        desktop.set_airplane(bool(on))


class Bridge(QObject):
    infoChanged = Signal()
    liveChanged = Signal()
    deskChanged = Signal()
    error = Signal(str)
    _request = Signal(str, "QVariantList")
    _stop = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._info: dict = {}
        self._live: dict = {}
        self._desk: dict = {}
        self._thread = QThread()
        self._worker = Worker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.start)
        self._worker.infoReady.connect(self._set_info)
        self._worker.liveReady.connect(self._set_live)
        self._worker.deskReady.connect(self._set_desk)
        self._worker.failed.connect(self.error)
        self._request.connect(self._worker.run)
        self._stop.connect(self._worker.stop)
        self._thread.start()

    def shutdown(self):
        self._stop.emit()
        self._thread.quit()
        self._thread.wait(2000)

    def _set_info(self, d):
        self._info = d
        self.infoChanged.emit()

    def _set_live(self, d):
        self._live = d
        self.liveChanged.emit()

    def _set_desk(self, d):
        self._desk = d
        self.deskChanged.emit()

    @Property("QVariantMap", notify=infoChanged)
    def info(self):
        return self._info

    @Property("QVariantMap", notify=liveChanged)
    def live(self):
        return self._live

    @Property("QVariantMap", notify=deskChanged)
    def desk(self):
        return self._desk

    @Property("QVariantMap", constant=True)
    def tr(self):
        return strings()

    @Slot(str, "QVariantList")
    def run(self, action: str, args: list):
        """QML: bridge.run("mode", ["performance"])"""
        self._request.emit(action, list(args))

    @Slot(str, "QVariant")
    def setDesk(self, key: str, value):
        """Kaydırıcılar akıcı görünsün diye değeri hemen yerelde günceller."""
        self._desk = dict(self._desk, **{key: value})
        self.deskChanged.emit()
