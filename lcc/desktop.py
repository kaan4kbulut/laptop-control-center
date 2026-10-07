"""Masaüstü düzeyindeki ayarlar: touchpad, mikrofon, ses, ekran parlaklığı, gece ışığı,
uçak modu, Num/Caps Lock göstergeleri.

Omarchy varsa onun komutları kullanılır (OSD ve kalıcı durum onlarda); yoksa genel
araçlara (wpctl, brightnessctl, nmcli, hyprctl) düşülür. Her okuma bilinmiyorsa None
döndürür; arayüz o denetimi devre dışı gösterir.
"""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import time

from .hardware import read_int

NIGHT_OFF = 6500     # K, gece ışığı kapalı
NIGHT_WARM = 3000    # K, kaydırıcının en sıcak ucu


def _run(*cmd: str, timeout: float = 3) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def _spawn(*cmd: str) -> bool:
    if not shutil.which(cmd[0]):
        return False
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return True


def _omarchy() -> bool:
    return shutil.which("omarchy") is not None


# --- touchpad --------------------------------------------------------------
_TOUCHPAD_STATE = os.path.expanduser("~/.local/state/omarchy/toggles/hypr/touchpad-disabled-name")


def touchpad() -> bool | None:
    if shutil.which("omarchy-toggle-touchpad"):
        return not os.path.exists(_TOUCHPAD_STATE)
    return None


def set_touchpad(on: bool) -> None:
    _spawn("omarchy-toggle-touchpad", "on" if on else "off")


# --- ses -------------------------------------------------------------------
def _wpctl_volume(target: str) -> tuple[float, bool] | None:
    out = _run("wpctl", "get-volume", target)
    m = re.search(r"Volume:\s*([0-9.]+)", out or "")
    if not m:
        return None
    return float(m.group(1)), "[MUTED]" in out


def volume() -> int | None:
    v = _wpctl_volume("@DEFAULT_AUDIO_SINK@")
    return None if v is None else round(v[0] * 100)


def set_volume(percent: int) -> None:
    p = max(0, min(100, int(percent)))
    _run("wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", f"{p}%")


def mic_on() -> bool | None:
    v = _wpctl_volume("@DEFAULT_AUDIO_SOURCE@")
    return None if v is None else not v[1]


def set_mic(on: bool) -> None:
    _run("wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0" if on else "1")


# --- ekran parlaklığı ------------------------------------------------------
def _backlight() -> str | None:
    devs = sorted(glob.glob("/sys/class/backlight/*"))
    # Gerçek panel denetleyicisi (intel_backlight, amdgpu_bl*) acpi_video'dan önce gelir.
    devs.sort(key=lambda d: os.path.basename(d).startswith("acpi_video"))
    return devs[0] if devs else None


def brightness() -> int | None:
    d = _backlight()
    if not d:
        return None
    cur, mx = read_int(d + "/brightness"), read_int(d + "/max_brightness")
    if cur is None or not mx:
        return None
    return round(cur * 100 / mx)


def set_brightness(percent: int) -> None:
    p = max(1, min(100, int(percent)))
    d = _backlight()
    # Okunan aygıtın kendisi ayarlansın (brightnessctl'nin varsayılanı başka olabilir).
    dev = ("-d", os.path.basename(d)) if d else ()
    _run("brightnessctl", "-q", *dev, "set", f"{p}%")


# --- gece ışığı ------------------------------------------------------------
def _sunset_temp() -> int | None:
    out = _run("hyprctl", "hyprsunset", "temperature")
    m = re.search(r"\d+", out or "")
    return int(m.group()) if m else None


def night_light() -> int | None:
    """0 (kapalı) … 100 (en sıcak). hyprsunset hiç yoksa None."""
    if not shutil.which("hyprsunset"):
        return None
    temp = _sunset_temp()
    if temp is None:
        return 0     # hyprsunset çalışmıyor: filtre yok
    if temp >= NIGHT_OFF:
        return 0
    return round((NIGHT_OFF - temp) * 100 / (NIGHT_OFF - NIGHT_WARM))


def set_night_light(level: int) -> None:
    level = max(0, min(100, int(level)))
    temp = round(NIGHT_OFF - (NIGHT_OFF - NIGHT_WARM) * level / 100)
    if _sunset_temp() is None:
        if level == 0:
            return
        launcher = ["uwsm-app", "--"] if shutil.which("uwsm-app") else []
        _spawn(*launcher, "hyprsunset")
        # Yeni başlayan hyprsunset açılış sonunda kendi varsayılanını uygular;
        # değer tutana kadar birkaç kez gönder.
        for _ in range(15):
            time.sleep(0.2)
            _run("hyprctl", "hyprsunset", "temperature", str(temp))
            if _sunset_temp() == temp:
                break
        return
    _run("hyprctl", "hyprsunset", "temperature", str(temp))


# --- uçak modu -------------------------------------------------------------
def airplane() -> bool | None:
    out = _run("nmcli", "-t", "radio", "all")
    if out is None:
        return None
    states = out.strip().split(":")
    # Çıktı: WIFI-HW:WIFI:WWAN-HW:WWAN — yazılımsal anahtarlar 1. ve 3. alanlar.
    soft = [s for i, s in enumerate(states) if i in (1, 3) and s != "missing"]
    return bool(soft) and all(s == "disabled" for s in soft)


def set_airplane(on: bool) -> None:
    _run("nmcli", "radio", "all", "off" if on else "on")
    if shutil.which("bluetoothctl"):
        _run("bluetoothctl", "power", "off" if on else "on")


# --- kilit göstergeleri ----------------------------------------------------
def _lock_led(name: str) -> bool | None:
    leds = glob.glob(f"/sys/class/leds/input*::{name}")
    if not leds:
        return None
    return any((read_int(p + "/brightness") or 0) > 0 for p in leds)


def num_lock() -> bool | None:
    return _lock_led("numlock")


def caps_lock() -> bool | None:
    return _lock_led("capslock")
