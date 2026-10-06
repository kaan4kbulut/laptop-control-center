"""Sistem diline göre Türkçe / İngilizce metinler."""

from __future__ import annotations

import locale
import os

_STRINGS: dict[str, tuple[str, str]] = {
    # anahtar: (türkçe, english)
    "app.title": ("Kontrol Merkezi", "Control Center"),
    "mode.performance": ("Performans", "Performance"),
    "mode.balanced": ("Eğlence", "Entertainment"),
    "mode.quiet": ("Sessiz", "Quiet"),
    "mode.powersave": ("Pil Tasarrufu", "Power Saving"),
    "mode.note.performance": ("en yüksek güç, fanlar daha sesli", "maximum power, louder fans"),
    "mode.note.balanced": ("dengeli, günlük kullanım", "balanced, everyday use"),
    "mode.note.quiet": ("en sessiz, düşük güç", "quietest, low power"),
    "mode.note.powersave": ("pilde en uzun süre", "longest battery life"),
    "fan.auto": ("Otomatik", "Automatic"),
    "fan.silent": ("Sessiz", "Silent"),
    "fan.max": ("Maksimum", "Maximum"),
    "fan.custom": ("Özel", "Custom"),
    "status.backend": ("Arka uç", "Backend"),
    "status.device": ("Cihaz", "Device"),
    "status.mode": ("Mod", "Mode"),
    "status.fan": ("Fan", "Fan"),
    "status.power": ("Güç kaynağı", "Power source"),
    "power.ac": ("Priz", "AC"),
    "power.battery": ("Pil", "Battery"),
    "cpu.freq": ("İşlemci frekansı", "CPU frequency"),
    "cpu.temp": ("Sıcaklık", "Temperature"),
    "cpu.usage": ("İşlemci kullanımı", "CPU usage"),
    "cpu.limit": ("İşlemci güç sınırı", "CPU power limit"),
    "gpu.usage": ("Ekran kartı kullanımı", "GPU usage"),
    "gpu.sleeping": ("Uykuda", "Sleeping"),
    "fan.cpu": ("İşlemci fanı", "CPU fan"),
    "fan.gpu": ("Ekran kartı fanı", "GPU fan"),
    "mem": ("RAM", "RAM"),
    "disk": ("Disk", "Disk"),
    "kbd": ("Klavye ışığı", "Keyboard backlight"),
    "charge.limit": ("Şarj sınırı", "Charge limit"),
    "unsupported": ("bu cihazda desteklenmiyor", "not supported on this device"),
    "setup.needed": ("Profiller kurulu değil; önce `lcc setup` çalıştırın.",
                     "Profiles are not installed; run `lcc setup` first."),
    "setup.done": ("Profiller kuruldu.", "Profiles installed."),
    # --- arayüz ---
    "nav.monitor": ("Sistem İzleme", "System Monitor"),
    "nav.led": ("LED Klavye", "LED Keyboard"),
    "nav.settings": ("Yapılandırma", "Settings"),
    "win.minimize": ("Küçült", "Minimize"),
    "win.maximize": ("Büyüt", "Maximize"),
    "win.close": ("Kapat", "Close"),
    "fan.control": ("FAN HIZ\nKONTROLÜ", "FAN SPEED\nCONTROL"),
    "fan.curve.edit": ("Fan eğrisini düzenle ›", "Edit fan curve ›"),
    "unit.ghz": ("×1000 MHz", "×1000 MHz"),
    "gpu.limit.upto": ("Güç sınırı {w} W'a kadar", "Power limit up to {w} W"),
    "gpu.short": ("Ekran kartı", "GPU"),
    "disk.label": ("Disk · {gb} GB", "Disk · {gb} GB"),
    "mem.label": ("RAM · {gb} GB", "RAM · {gb} GB"),
    "led.color.selected": ("Seçili renk", "Selected color"),
    "led.color.custom": ("Özel renk…", "Custom color…"),
    "led.brightness": ("Parlaklık", "Brightness"),
    "led.off": ("Kapalı", "Off"),
    "toggle.fnlock": ("Fn tuş kilidi", "Fn lock"),
    "toggle.fnlock.hint": ("F1–F12 tuşları Fn olmadan medya tuşu gibi çalışır.",
                           "F1–F12 act as media keys without holding Fn."),
    "toggle.touchpad": ("Touchpad", "Touchpad"),
    "toggle.touchpad.hint": ("Dokunmatik yüzeyi açar veya kapatır.", "Turns the touchpad on or off."),
    "toggle.airplane": ("Uçak modu", "Airplane mode"),
    "toggle.airplane.hint": ("Wi-Fi ve Bluetooth birlikte kapanır.", "Turns Wi-Fi and Bluetooth off together."),
    "toggle.mic": ("Mikrofon", "Microphone"),
    "toggle.mic.hint": ("Dahili mikrofonu susturur.", "Mutes the microphone."),
    "toggle.numlock": ("Num Lock", "Num Lock"),
    "toggle.capslock": ("Caps Lock", "Caps Lock"),
    "toggle.indicator.hint": ("Gösterge; tuşla değişir.", "Indicator; changes with the key."),
    "state.on": ("AÇIK", "ON"),
    "state.off": ("KAPALI", "OFF"),
    "gpu.mode": ("Ekran Kartı Modu", "GPU Mode"),
    "gpu.mode.dgpu": ("Sadece harici ekran kartı", "Discrete GPU only"),
    "gpu.mode.hybrid": ("Hibrit (Intel + NVIDIA)", "Hybrid (iGPU + NVIDIA)"),
    "gpu.mode.note": ("Linux'ta geçiş henüz desteklenmiyor.", "Switching is not supported on Linux yet."),
    "charge.title": ("Şarj Sınırı", "Charge Limit"),
    "charge.full": ("Tam (%100)", "Full (100%)"),
    "charge.note": ("Pil bu yüzdeye ulaşınca şarj durur; prizde uzun kullanımda pil ömrünü uzatır.",
                    "Charging stops at this level; extends battery life when mostly plugged in."),
    "night": ("Gece ışığı", "Night light"),
    "night.off": ("Kapalı", "Off"),
    "night.warm": ("Sıcak", "Warm"),
    "volume": ("Ses", "Volume"),
    "screen.brightness": ("Ekran parlaklığı", "Screen brightness"),
    "color.ff3600": ("Turuncu-kırmızı", "Orange-red"),
    "color.ff8a00": ("Turuncu", "Orange"),
    "color.ffd000": ("Sarı", "Yellow"),
    "color.b6ff00": ("Fıstık yeşili", "Lime"),
    "color.22e55a": ("Yeşil", "Green"),
    "color.00e5c0": ("Turkuaz", "Turquoise"),
    "color.00c8ff": ("Camgöbeği", "Cyan"),
    "color.2f6bff": ("Mavi", "Blue"),
    "color.5a3dff": ("Lacivert", "Indigo"),
    "color.a23dff": ("Mor", "Purple"),
    "color.ff2dd2": ("Pembe", "Pink"),
    "color.ffffff": ("Beyaz", "White"),
    "nav.power": ("Pil Tasarrufu", "Power Saving"),
    "power.title": ("Pil tasarrufu", "Power saving"),
    "power.off": ("Kapalı", "Off"),
    "power.saver": ("Tasarruf", "Saver"),
    "power.ultra": ("Ultra", "Ultra"),
    "power.auto": ("Otomatik", "Automatic"),
    "power.request": ("istek", "request"),
    "power.requested": ("İstek gönderildi: {level}", "Requested: {level}"),
    "power.failed": ("Uygulanamayan", "Could not apply"),
    "power.auto.label": ("Pilde kendiliğinden Tasarruf'a geç", "Switch to Saver automatically on battery"),
    "power.auto.hint": ("Fiş takılınca her şey eski haline döner.", "Everything is restored when plugged in."),
    "power.now": ("Şu an", "Now"),
    "power.onac": ("Prizde", "Plugged in"),
    "power.onbat": ("Pilde", "On battery"),
    "power.draw": ("Tüketim", "Power draw"),
    "power.left": ("Kalan süre", "Time left"),
    "power.cap": ("Parlaklık sınırı", "Brightness cap"),
    "power.helper.missing": ("Root gerektiren ayarlar için yardımcı kurulu değil.", "Helper for root settings is not installed."),
    "power.f.refresh": ("Ekran 60 Hz", "Display 60 Hz"),
    "power.f.refresh.hint": ("Yüksek tazeleme hızı pil tüketir.", "High refresh rate costs battery."),
    "power.f.brightness": ("Parlaklık sınırı", "Brightness cap"),
    "power.f.brightness.hint": ("Ekran bu yüzdenin üstüne çıkmaz.", "Screen is dimmed to this level."),
    "power.f.wifi": ("Wi-Fi güç tasarrufu", "Wi-Fi power saving"),
    "power.f.wifi.hint": ("Boştayken Wi-Fi kartı uyur.", "Wi-Fi card sleeps when idle."),
    "power.f.aspm": ("PCIe güç yönetimi", "PCIe power management"),
    "power.f.aspm.hint": ("ASPM en tasarruflu düzeyde.", "ASPM at its most frugal level."),
    "power.f.services": ("Arka plan servisleri", "Background services"),
    "power.f.services.hint": ("nvidia-powerd, avahi, cups, ollama durur.", "Stops nvidia-powerd, avahi, cups, ollama."),
    "power.f.bluetooth": ("Bluetooth kapalı", "Bluetooth off"),
    "power.f.bluetooth.hint": ("Önceden açıksa fişte geri açılır.", "Turned back on when plugged in if it was on."),
    "power.f.kbd": ("Klavye ışığı kapalı", "Keyboard light off"),
    "power.f.kbd.hint": ("Fişte eski parlaklığına döner.", "Restored when plugged in."),
    "power.f.ecores": ("Yalnız verimli çekirdekler", "Efficiency cores only"),
    "power.f.ecores.hint": ("Uygulamalar E çekirdeklerde çalışır; yavaşlar.", "Apps run on E-cores; slower."),
    "battery.short": ("Pil", "Battery"),
}


def strings() -> dict[str, str]:
    """Etkin dildeki bütün metinler (QML için)."""
    i = 0 if LANG == "tr" else 1
    return {k: v[i] for k, v in _STRINGS.items()}


def _keyboard_is_turkish() -> bool:
    """Sistem dili İngilizce bırakılmış Türk kullanıcılar için klavye düzenine bakar."""
    for path in ("/etc/vconsole.conf", "/etc/X11/xorg.conf.d/00-keyboard.conf",
                 "/etc/default/keyboard"):
        try:
            with open(path) as f:
                for line in f:
                    low = line.lower().replace('"', " ").replace("=", " ").split()
                    if len(low) >= 2 and low[0] in ("keymap", "xkblayout", "option") \
                            and low[-1].startswith("tr"):
                        return True
        except OSError:
            pass
    return False


def _detect_lang() -> str:
    from . import config
    pref = config.load().get("language", "auto")
    if pref in ("tr", "en"):
        return pref
    for var in ("LCC_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        v = os.environ.get(var)
        if v:
            if v.lower().startswith("tr"):
                return "tr"
            break
    else:
        loc = locale.getlocale()[0] or ""
        if loc.lower().startswith("tr"):
            return "tr"
    return "tr" if _keyboard_is_turkish() else "en"


LANG = _detect_lang()


def t(key: str, **kw) -> str:
    pair = _STRINGS.get(key)
    if pair is None:
        return key
    s = pair[0] if LANG == "tr" else pair[1]
    return s.format(**kw) if kw else s
