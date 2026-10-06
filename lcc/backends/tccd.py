"""Clevo / Tuxedo arka ucu: TUXEDO Control Center servisi (tccd) üzerinden DBus.

Mod ve fan değiştirmek root istemez: kurulumda her (mod, fan) birleşimi için bir tccd
profili yazılır (`lcc-<mod>-<fan>`), çalışırken `SetTempProfileById` ile seçilir.
tccd, fiş takılıp çekilince geçici profili sıfırlayıp ayarlardaki profile döner;
`lcc daemon` bu anda kullanıcının seçimini yeniden uygular.
"""

from __future__ import annotations

import copy
import glob
import json
import os
import subprocess
import tempfile

from gi.repository import GLib

from .. import dbus
from ..hardware import read, read_int
from ..i18n import t
from .base import (FAN_MODES, Backend, Capabilities, KeyboardCaps, KeyboardState,
                   SetupRequired, Unsupported)

BUS = "com.tuxedocomputers.tccd"
PATH = "/com/tuxedocomputers/tccd"
IFACE = "com.tuxedocomputers.tccd"
TCCD_EXEC = "/opt/tuxedo-control-center/resources/dist/tuxedo-control-center/data/service/tccd"
PREFIX = "lcc-"

# Ortak mod -> tccd ODM profili
ODM = {"performance": "performance", "balanced": "entertainment",
       "quiet": "quiet", "powersave": "power_saving"}

CPU = {
    "performance": {"energyPerformancePreference": "performance", "noTurbo": False},
    "balanced": {"energyPerformancePreference": "balance_performance", "noTurbo": False},
    "quiet": {"energyPerformancePreference": "balance_power", "noTurbo": False},
    "powersave": {"energyPerformancePreference": "power", "noTurbo": True},
}

# tccd'nin hazır fan profilleri; "auto", "max" ve "custom" kendi eğrimizle "Custom" olur.
FAN_PRESET = {"silent": "Silent"}

# "Otomatik" fan her modda o modun karakterinde çalışır: Performans daha erken ve
# güçlü soğutur, Sessiz geç devreye girer. (sıcaklık °C, hız %) noktaları.
AUTO_CURVE = {
    "performance": [[20, 15], [40, 28], [50, 38], [60, 50], [70, 65], [80, 85], [90, 100], [100, 100]],
    # tccd'nin "Balanced" eğrisiyle aynı
    "balanced": [[20, 12], [30, 14], [40, 22], [50, 35], [60, 44], [70, 56], [80, 79], [90, 85], [100, 90]],
    "quiet": [[20, 0], [40, 10], [50, 18], [60, 28], [70, 42], [80, 62], [90, 82], [100, 100]],
}
AUTO_CURVE["powersave"] = AUTO_CURVE["quiet"]


def _call(method, sig=None, *args):
    return dbus.call(BUS, PATH, IFACE, method, sig, *args)


def _json(method):
    return json.loads(_call(method))


def profile_id(mode: str, fan: str) -> str:
    return f"{PREFIX}{mode}-{fan}"


def parse_profile_id(pid: str) -> tuple[str | None, str | None]:
    if not pid.startswith(PREFIX):
        return None, None
    rest = pid[len(PREFIX):]
    for fan in FAN_MODES:
        if rest.endswith("-" + fan):
            return rest[: -len(fan) - 1], fan
    return None, None


def expand_curve(points: list[list[int]]) -> list[dict]:
    """(sıcaklık, hız) noktalarından 0–100 °C için derece başına tablo üretir."""
    pts = sorted((int(a), int(b)) for a, b in points)
    table = []
    for temp in range(0, 101):
        if temp <= pts[0][0]:
            speed = pts[0][1]
        elif temp >= pts[-1][0]:
            speed = pts[-1][1]
        else:
            for (t0, s0), (t1, s1) in zip(pts, pts[1:]):
                if t0 <= temp <= t1:
                    speed = s0 + (s1 - s0) * (temp - t0) / max(1, t1 - t0)
                    break
        table.append({"temp": temp, "speed": max(0, min(100, round(speed)))})
    return table


class TccdBackend(Backend):
    id = "tccd"
    name = "Clevo / TUXEDO (tccd)"

    @classmethod
    def probe(cls) -> int:
        if not dbus.has_name(BUS):
            return 0
        try:
            return 80 if _call("TuxedoWmiAvailable") else 40
        except GLib.Error:
            return 0

    def __init__(self):
        self._odm = list(_call("ODMProfilesAvailable") or [])

    # --- yetenekler --------------------------------------------------------
    def capabilities(self) -> Capabilities:
        modes = [m for m, o in ODM.items() if o in self._odm] or list(ODM)
        kb = None
        try:
            c = _json("GetKeyboardBacklightCapabilitiesJSON")
            if c:
                kb = KeyboardCaps(brightness_max=int(c.get("maxBrightness", 0)),
                                  color=int(c.get("maxRed", 0)) > 0,
                                  zones=int(c.get("zones", 1)))
        except (GLib.Error, ValueError):
            pass
        try:
            ends = json.loads(_call("GetChargeEndAvailableThresholds"))
            starts = json.loads(_call("GetChargeStartAvailableThresholds"))
        except (GLib.Error, ValueError):
            ends, starts = [], []
        try:
            fn = bool(_call("GetFnLockSupported"))
        except GLib.Error:
            fn = False
        return Capabilities(modes=modes, fan_modes=list(FAN_MODES), keyboard=kb,
                            charge_end=ends, charge_start=starts, fn_lock=fn)

    # --- profiller ---------------------------------------------------------
    def _installed_ids(self) -> set[str]:
        return {p["id"] for p in _json("GetCustomProfilesJSON")}

    def needs_setup(self) -> bool:
        want = {profile_id(m, f) for m in self.capabilities().modes for f in FAN_MODES}
        return not want <= self._installed_ids()

    def current(self):
        active = _json("GetActiveProfileJSON")
        return parse_profile_id(active.get("id", ""))

    def apply(self, mode: str, fan: str, force: bool = False) -> None:
        pid = profile_id(mode, fan)
        if pid not in self._installed_ids():
            raise SetupRequired(t("setup.needed"))
        if self.current() == (mode, fan) and not force:
            return
        if not _call("SetTempProfileById", "s", pid):
            raise RuntimeError(f"tccd rejected profile {pid}")

    def auto_curves(self) -> dict[str, list[list[int]]]:
        """Arayüzde karşılaştırma için modların Otomatik fan eğrileri."""
        return {m: AUTO_CURVE[m] for m in self.capabilities().modes if m in AUTO_CURVE}

    def build_profiles(self, custom_curve: list[list[int]]) -> list[dict]:
        base = _json("GetDefaultValuesProfileJSON")
        # Kayıtlı profillerdeki gibi frekans/çekirdek alanları boş bırakılır; aksi halde tccd
        # açılış anındaki (turbo kapalıyken düşük) frekansı sınır olarak uygular.
        for k in ("onlineCores", "scalingMinFrequency", "scalingMaxFrequency"):
            base["cpu"].pop(k, None)
        base["webcam"]["useStatus"] = False
        base["display"].update(useBrightness=False, useRefRate=False, useResolution=False)
        tables = {
            "max": expand_curve([[0, 100], [100, 100]]),
            "custom": expand_curve(custom_curve),
        }
        out = []
        for mode in self.capabilities().modes:
            for fan in FAN_MODES:
                p = copy.deepcopy(base)
                p["id"] = profile_id(mode, fan)
                p["name"] = f"LCC {t('mode.' + mode)} · {t('fan.' + fan)}"
                p["description"] = "laptop-control-center"
                p["cpu"].update(CPU[mode])
                if ODM[mode] in self._odm:
                    p["odmProfile"] = {"name": ODM[mode]}
                f = p["fan"]
                f.update(useControl=True, minimumFanspeed=0, maximumFanspeed=100,
                         offsetFanspeed=0)
                if fan in FAN_PRESET:
                    f["fanProfile"] = FAN_PRESET[fan]
                else:
                    table = expand_curve(AUTO_CURVE[mode]) if fan == "auto" else tables[fan]
                    f["fanProfile"] = "Custom"
                    f["customFanCurve"] = {"tableCPU": table, "tableGPU": table}
                out.append(p)
        return out

    def setup(self, custom_curve=None) -> None:
        """Profilleri tccd'ye yazar (pkexec ile tek parola sorusu). Kullanıcının kendi
        profillerine dokunmaz; eski lcc-* profilleri yenileriyle değiştirilir."""
        from .. import config
        conf = config.load()
        curve = custom_curve or conf["custom_fan_curve"]
        ours = self.build_profiles(curve)
        others = [p for p in _json("GetCustomProfilesJSON") if not p["id"].startswith(PREFIX)]
        settings = _json("GetSettingsJSON")
        ac, bat = conf["ac"], conf["battery"]
        settings["stateMap"] = {
            "power_ac": profile_id(ac["mode"], ac["fan"]),
            "power_bat": profile_id(bat["mode"], bat["fan"]),
        }
        with tempfile.TemporaryDirectory(prefix="lcc-") as d:
            os.chmod(d, 0o755)
            pf, sf = os.path.join(d, "profiles.json"), os.path.join(d, "settings.json")
            with open(pf, "w") as f:
                json.dump(others + ours, f)
            with open(sf, "w") as f:
                json.dump(settings, f)
            os.chmod(pf, 0o644)
            os.chmod(sf, 0o644)
            from .. import helper
            if helper.installed() and helper.version() >= 2:
                # Yardımcı kuruluysa parola sorulmaz (fan eğrisi kaydı gibi sık işler için).
                cmd = ["pkexec", helper.PATH, "tcc-profiles", pf, sf]
            else:
                cmd = ["pkexec", TCCD_EXEC, "--new_profiles", pf, "--new_settings", sf]
            r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout).strip() or f"pkexec exit {r.returncode}")

    # --- izleme ------------------------------------------------------------
    def start_monitoring(self) -> None:
        try:
            _call("SetSensorDataCollectionStatus", "b", True)
        except GLib.Error:
            pass

    def stop_monitoring(self) -> None:
        try:
            _call("SetSensorDataCollectionStatus", "b", False)
        except GLib.Error:
            pass

    def fan_speeds(self) -> dict[str, float]:
        try:
            data = _json("GetFanDataJSON")
        except (GLib.Error, ValueError):
            return {}
        names = {"cpu": "cpu", "gpu1": "gpu", "gpu2": "gpu2"}
        out = {}
        for k, v in data.items():
            speed = v.get("speed", {}).get("data", -1)
            if speed is not None and speed >= 0 and k in names:
                out[names[k]] = float(speed)
        # gpu2 yalnızca gerçekten ikinci bir fan varsa anlamlı (sıcaklığı > 0).
        if data.get("gpu2", {}).get("temp", {}).get("data", 0) <= 0:
            out.pop("gpu2", None)
        return out

    # --- klavye ------------------------------------------------------------
    def keyboard(self) -> KeyboardState:
        states = _json("GetKeyboardBacklightStatesJSON")
        if not states:
            raise Unsupported
        s = states[0]
        state = KeyboardState(brightness=int(s["brightness"]),
                              color="#{:02x}{:02x}{:02x}".format(s["red"], s["green"], s["blue"]))
        # tccd yalnızca kendi yazdığı değeri bilir; Fn tuşu veya boşta kısma gerçek
        # değeri değiştirmiş olabilir. LED sysfs'te varsa oradan okunur.
        led = next(iter(glob.glob("/sys/class/leds/*kbd_backlight")), None)
        if led:
            b = read_int(led + "/brightness")
            if b is not None:
                state.brightness = b
            rgb = (read(led + "/multi_intensity") or "").split()
            if len(rgb) == 3:
                state.color = "#{:02x}{:02x}{:02x}".format(*map(int, rgb))
        return state

    def set_keyboard(self, state: KeyboardState) -> None:
        c = state.color.lstrip("#")
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
        caps = self.capabilities().keyboard
        zones = caps.zones if caps else 1
        payload = [{"mode": 0, "brightness": int(state.brightness),
                    "red": r, "green": g, "blue": b}] * zones
        if not _call("SetKeyboardBacklightStatesJSON", "s", json.dumps(payload)):
            raise RuntimeError("tccd rejected keyboard state")

    # --- şarj --------------------------------------------------------------
    def charge_thresholds(self):
        try:
            return int(_call("GetChargeStartThreshold")), int(_call("GetChargeEndThreshold"))
        except GLib.Error:
            return None, None

    def set_charge_end(self, value: int) -> None:
        caps = self.capabilities()
        if value not in caps.charge_end:
            raise Unsupported(f"{value} ∉ {caps.charge_end}")
        # Başlangıç eşiği bitişten küçük olmalı; en yakın alttaki geçerli değere çek.
        start, _ = self.charge_thresholds()
        lower = [s for s in caps.charge_start if s < value]
        if start is not None and start >= value and lower:
            _call("SetChargeStartThreshold", "i", max(lower))
        if not _call("SetChargeEndThreshold", "i", value):
            raise RuntimeError("tccd rejected charge threshold")

    # --- Fn kilidi ---------------------------------------------------------
    def fn_lock(self) -> bool:
        return bool(_call("GetFnLockStatus"))

    def set_fn_lock(self, on: bool) -> None:
        _call("SetFnLockStatus", "b", bool(on))
