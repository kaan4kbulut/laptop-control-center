"""Pil tasarrufu: pilde kendiliğinden "Tasarruf", istenirse "Ultra"; prize takılınca geri alınır.

Kademe (level): off | saver | ultra | headless. Her kademenin açacağı özellikler config.json'daki
`power_saving` bölümünde, kullanıcı arayüzden değiştirebilir. Uygulayan tek yer
servis (lcc daemon); arayüz ve komut satırı yalnızca istek dosyasını yazar.

Her özellik açılmadan önceki durumu durum dosyasına kaydeder ve kapanınca oraya döner:
önceden kapalı olan Bluetooth açılmaz, önceden çalışmayan servis başlatılmaz, kullanıcı
parlaklığı sonradan elle değiştirdiyse eski değere zorlanmaz.

"Ekransız" (headless) kademe elle seçilmez: pildeyken kapak kapanınca (harici ekran
yoksa) kendiliğinden açılır, kapak açılınca ya da fiş takılınca kapanır. Ekranı kapatır,
tarayıcı gibi uygulamaları dondurur; bilgisayar kapak kapalı arkada iş yaparken içindir.

Root gereken adımlar lcc-helper ile yapılır (lcc/helper.py).
"""

from __future__ import annotations

import glob
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import config, desktop, helper

log = logging.getLogger("lcc.power")

LEVELS = ("off", "saver", "ultra", "headless")
FEATURES = ("refresh", "brightness", "wifi", "aspm", "services", "bluetooth", "kbd", "ecores",
            "dpms", "freeze")
ROOT_FEATURES = {"wifi", "aspm", "services", "bluetooth", "ecores"}
# Yeniden başlatınca kendiliğinden eski haline dönenler (durumları açılışta unutulur).
BOOT_RESET = ROOT_FEATURES | {"dpms", "freeze"}
MANUAL = ("off", "saver", "ultra")     # elle istenebilenler
SERVICES = ("nvidia-powerd", "avahi-daemon", "cups", "ollama")
SAVER_REFRESH = 60


STATE_FILE = config.state_dir() / "power.json"
REQUEST_FILE = config.state_dir() / "power-request"


def _run(*cmd: str, timeout: float = 10) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("%s: %s", cmd[0], e)
        return None
    if r.returncode != 0:
        log.warning("%s failed (%s): %s", " ".join(cmd), r.returncode, r.stderr.strip())
        return None
    return r.stdout


def _helper(*args: str) -> bool:
    return helper.run(*args)


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return ""


# --- ayarlar, istek ve durum ---------------------------------------------------
def settings() -> dict:
    return config.load()["power_saving"]


def request(level: str) -> None:
    """Arayüz/komut satırı: 'auto' (pil durumuna göre) veya off/saver/ultra."""
    if level not in MANUAL + ("auto",):
        raise ValueError(level)
    REQUEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    REQUEST_FILE.write_text(level + "\n")


def requested() -> str:
    try:
        v = REQUEST_FILE.read_text().strip()
    except OSError:
        return "auto"
    return v if v in MANUAL else "auto"


def status() -> dict:
    """Servisin yazdığı son durum: {'level', 'active': [...], 'requested'}."""
    try:
        st = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        st = {}
    return {"level": st.get("level", "off"), "active": sorted(st.get("saved", {})),
            "requested": requested(), "failed": st.get("failed", [])}


def helper_installed() -> bool:
    return helper.installed()


def ecores() -> str | None:
    """Verimli çekirdekler (Intel hibrit). Yoksa None."""
    try:
        cpus = Path("/sys/devices/cpu_atom/cpus").read_text().strip()
    except OSError:
        return None
    return cpus if re.fullmatch(r"[0-9,-]+", cpus) else None


def available(backend=None) -> dict[str, bool]:
    root = helper_installed() and shutil.which("pkexec") is not None
    kbd = False
    if backend is not None:
        try:
            backend.keyboard()
            kbd = True
        except Exception:
            pass
    return {
        "refresh": shutil.which("hyprctl") is not None,
        "brightness": desktop.brightness() is not None,
        "wifi": root and shutil.which("iw") is not None,
        "aspm": root and os.path.exists("/sys/module/pcie_aspm/parameters/policy"),
        "services": root,
        "bluetooth": root and bool(_rfkill_bluetooth()),
        "kbd": kbd,
        "ecores": root and ecores() is not None,
        "dpms": shutil.which("hyprctl") is not None,
        "freeze": shutil.which("systemctl") is not None,
    }


# --- okumalar -------------------------------------------------------------------
def _wifi_ifaces() -> list[str]:
    return re.findall(r"^\s*Interface\s+(\S+)", _run("iw", "dev") or "", re.M)


def _wifi_powersave() -> str:
    for dev in _wifi_ifaces():
        out = _run("iw", "dev", dev, "get", "power_save") or ""
        if "on" in out.lower().split():
            return "on"
    return "off"


def _aspm() -> str | None:
    try:
        m = re.search(r"\[(\w+)\]", Path("/sys/module/pcie_aspm/parameters/policy").read_text())
    except OSError:
        return None
    return m.group(1) if m else None


def _rfkill_bluetooth() -> list[str]:
    return [os.path.dirname(t) for t in glob.glob("/sys/class/rfkill/rfkill*/type")
            if Path(t).read_text().strip() == "bluetooth"]


def _bluetooth_blocked() -> bool:
    devs = _rfkill_bluetooth()
    return bool(devs) and all(Path(d, "soft").read_text().strip() == "1" for d in devs)


def _active_services() -> list[str]:
    out = []
    for s in SERVICES:
        r = subprocess.run(["systemctl", "is-active", "--quiet", s + ".service"])
        if r.returncode == 0:
            out.append(s)
    return out


# --- ekran ve uygulamalar (ekransız kademe) -----------------------------------------
def _monitors() -> list[dict]:
    out = _run("hyprctl", "monitors", "-j")
    return json.loads(out) if out else []


def set_dpms(on: bool) -> None:
    action = "on" if on else "off"
    for m in _monitors():
        _run("hyprctl", "dispatch", f'hl.dsp.dpms({{ action = "{action}", monitor = "{m["name"]}" }})')


def lid_closed() -> bool:
    for f in glob.glob("/proc/acpi/button/lid/*/state"):
        try:
            if "closed" in Path(f).read_text():
                return True
        except OSError:
            pass
    return False


def external_display() -> bool:
    internal = (_run("omarchy-hyprland-monitor-laptop") or "").strip()
    return any(m["name"] != internal and not m["name"].startswith("eDP") for m in _monitors())


def lid_headless(on_battery: bool) -> bool:
    """Pilde, kapak kapalı ve harici ekran yokken ekransız kademe."""
    return (on_battery and settings().get("headless_on_lid", True) and lid_closed()
            and not external_display())


def _app_scopes(names: list[str]) -> list[str]:
    """Adı listedeki bir uygulamayı içeren kullanıcı scope'ları (ör. app-...Chrome-1234.scope)."""
    out = _run("systemctl", "--user", "list-units", "--type=scope", "--state=running",
               "--no-legend", "--plain") or ""
    units = [line.split()[0] for line in out.splitlines() if line.strip()]
    keys = [n.lower() for n in names]
    return [u for u in units if u.startswith("app-") and any(k in u.lower() for k in keys)]


def _freeze(units: list[str], on: bool) -> list[str]:
    done = []
    for u in units:
        if _run("systemctl", "--user", "freeze" if on else "thaw", u) is not None:
            done.append(u)
    return done


# --- iç ekran tazeleme hızı (eski power-watch) -------------------------------------
def _laptop_monitor() -> dict | None:
    out = _run("hyprctl", "monitors", "-j")
    if not out:
        return None
    mons = json.loads(out)
    name = (_run("omarchy-hyprland-monitor-laptop") or "").strip()
    for m in mons:
        if m["name"] == name or (not name and m["name"].startswith("eDP")):
            return m
    return None


def set_refresh(low: bool) -> None:
    """low: iç ekranı 60 Hz'e al; değilse en yüksek tazelemeye döndür."""
    m = _laptop_monitor()
    if not m:
        return
    rate = int(m["refreshRate"])
    w, h, x, y, scale = m["width"], m["height"], m["x"], m["y"], m["scale"]
    if low:
        if rate == SAVER_REFRESH:
            return
        mode = f"{w}x{h}@{SAVER_REFRESH}"
    else:
        rates = [float(r) for r in re.findall(r"@([0-9.]+)", " ".join(m.get("availableModes", [])))]
        if not rates or rate >= int(max(rates)) - 1:
            return
        mode = "preferred"
    _run("hyprctl", "eval",
         f'hl.monitor({{ output = "{m["name"]}", mode = "{mode}", position = "{x}x{y}", scale = {scale} }})')
    log.info("internal display -> %s", mode)


# --- yönetici -------------------------------------------------------------------
class PowerManager:
    def __init__(self, backend=None):
        self.backend = backend
        self.saved: dict = {}       # özellik -> açılmadan önceki durum
        self.level = "off"
        self.cap: int | None = None
        self.failed: list[str] = []
        self._load()

    def _load(self) -> None:
        try:
            st = json.loads(STATE_FILE.read_text())
        except (OSError, ValueError):
            return
        self.saved = st.get("saved", {})
        self.level = st.get("level", "off")
        self.cap = st.get("cap")
        if st.get("boot") != _boot_id():
            # Yeniden başlatma root ayarlarını zaten sıfırladı; onları geri almaya çalışma.
            for f in BOOT_RESET:
                self.saved.pop(f, None)

    def _save(self) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"level": self.level, "saved": self.saved, "cap": self.cap,
                                   "failed": self.failed, "boot": _boot_id()}, indent=2))
        os.replace(tmp, STATE_FILE)

    def desired_level(self, on_battery: bool) -> str:
        if lid_headless(on_battery):
            return "headless"
        req = requested()
        if req in LEVELS:
            return req
        return "saver" if on_battery and settings().get("auto", True) else "off"

    def on_power_source_changed(self, on_battery: bool) -> None:
        """Fiş takılınca/çekilince elle seçim unutulur, otomatik kurala dönülür."""
        try:
            REQUEST_FILE.unlink()
        except OSError:
            pass
        self.evaluate(on_battery)

    def evaluate(self, on_battery: bool) -> None:
        conf = settings()
        level = self.desired_level(on_battery)
        avail = available(self.backend)
        want = set() if level == "off" else {f for f in conf.get(level, []) if avail.get(f)}
        cap = int(conf.get("brightness_cap", {}).get(level, 50)) if level != "off" else None

        self.failed = []
        for f in [f for f in FEATURES if f in self.saved and f not in want]:
            self._revert(f)
        for f in [f for f in FEATURES if f in want and f not in self.saved]:
            self._apply(f, cap)
        if "brightness" in want and "brightness" in self.saved and cap != self.cap:
            self._cap_brightness(cap)
        self.cap = cap if "brightness" in self.saved else None
        if level != self.level:
            log.info("power saving level: %s -> %s (%s)", self.level, level, sorted(want))
        self.level = level
        self.ensure_refresh()
        self._save()

    def ensure_refresh(self) -> None:
        set_refresh("refresh" in self.saved)


    # --- tek tek özellikler ------------------------------------------------------
    def _apply(self, f: str, cap: int | None) -> None:
        ok, prev = True, None
        if f == "refresh":
            prev = True
        elif f == "brightness":
            prev = desktop.brightness()
            ok = prev is not None
            if ok:
                self.cap = None
                self._cap_brightness(cap)
        elif f == "wifi":
            prev = _wifi_powersave()
            ok = _helper("wifi-powersave", "on")
        elif f == "aspm":
            prev = _aspm()
            ok = prev is not None and _helper("aspm", "powersupersave")
        elif f == "services":
            prev = _active_services()
            for s in prev:
                ok = _helper("service", "stop", s) and ok
        elif f == "bluetooth":
            prev = _bluetooth_blocked()
            ok = prev or _helper("rfkill", "bluetooth", "block")
        elif f == "kbd":
            try:
                k = self.backend.keyboard()
                prev = k.brightness
                if k.brightness:
                    k.brightness = 0
                    self.backend.set_keyboard(k)
            except Exception as e:
                log.warning("kbd: %s", e)
                ok = False
        elif f == "ecores":
            prev = True
            ok = _helper("cpus", ecores() or "all")
        elif f == "freeze":
            prev = _freeze(_app_scopes(settings().get("freeze_apps", [])), True)
            log.info("frozen: %s", prev)
        elif f == "dpms":
            prev = True
            set_dpms(False)
        if ok:
            self.saved[f] = prev
        else:
            self.failed.append(f)
            log.warning("could not enable %s", f)

    def _revert(self, f: str) -> None:
        prev = self.saved.pop(f)
        if f == "brightness":
            cur = desktop.brightness()
            # Kullanıcı sınırdan sonra elle değiştirdiyse dokunma.
            if prev is not None and cur is not None and self.cap is not None and abs(cur - self.cap) <= 1 and cur < prev:
                desktop.set_brightness(prev)
            self.cap = None
        elif f == "wifi":
            _helper("wifi-powersave", prev if prev in ("on", "off") else "off")
        elif f == "aspm":
            if prev:
                _helper("aspm", prev)
        elif f == "services":
            for s in prev or []:
                _helper("service", "start", s)
        elif f == "bluetooth":
            if prev is False:
                _helper("rfkill", "bluetooth", "unblock")
        elif f == "kbd":
            try:
                k = self.backend.keyboard()
                if not k.brightness and prev:
                    k.brightness = int(prev)
                    self.backend.set_keyboard(k)
            except Exception as e:
                log.warning("kbd restore: %s", e)
        elif f == "ecores":
            _helper("cpus", "all")
        elif f == "freeze":
            _freeze(prev or [], False)
        elif f == "dpms":
            set_dpms(True)

    def _cap_brightness(self, cap: int | None) -> None:
        cur = desktop.brightness()
        if cap is not None and cur is not None and cur > cap:
            desktop.set_brightness(cap)
        self.cap = cap
