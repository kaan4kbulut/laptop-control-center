"""Kullanıcı ayarları ve son seçilen modlar (~/.config/laptop-control-center/config.json)."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULTS: dict = {
    "language": "auto",          # auto | tr | en
    # Güç kaynağına göre hatırlanan seçim; fiş takılıp çekilince yeniden uygulanır.
    "ac": {"mode": "performance", "fan": "auto"},
    "battery": {"mode": "powersave", "fan": "silent"},
    # Özel fan eğrisi: (sıcaklık °C, hız %) noktaları
    "custom_fan_curve": [[20, 0], [40, 15], [50, 25], [60, 35], [70, 50],
                         [80, 70], [90, 90], [100, 100]],
    "keyboard": {"color": "#ff3600", "brightness": 100},
    "camera": True,              # False: açılışta da kapalı tutulur
    # Pil tasarrufu kademeleri: her biri açacağı özelliklerin listesi (lcc/power.py).
    "power_saving": {
        "auto": True,            # pilde kendiliğinden "saver"
        "saver": ["refresh", "brightness", "wifi", "aspm", "services"],
        "ultra": ["refresh", "brightness", "wifi", "aspm", "services", "bluetooth", "kbd", "ecores"],
        # Pilde kapak kapanınca (harici ekran yoksa) kendiliğinden "headless".
        "headless_on_lid": True,
        "headless": ["refresh", "wifi", "aspm", "services", "bluetooth", "kbd", "ecores",
                     "dpms", "freeze"],
        "brightness_cap": {"saver": 50, "ultra": 30},
        # Ekransızda dondurulan uygulamalar (scope adında geçen); terminaller dondurulmaz.
        "freeze_apps": ["chrome", "chromium", "brave", "firefox", "zen", "librewolf",
                        "telegram", "signal", "discord", "slack", "spotify", "obsidian",
                        "typora", "libreoffice", "steam"],
    },
}


def path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "laptop-control-center" / "config.json"


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "laptop-control-center"


def load() -> dict:
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(path()) as f:
            user = json.load(f)
    except (OSError, ValueError):
        return data
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k].update(v)
        else:
            data[k] = v
    return data


def save(data: dict) -> None:
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, p)


def update(**changes) -> dict:
    data = load()
    for k, v in changes.items():
        if isinstance(v, dict) and isinstance(data.get(k), dict):
            data[k].update(v)
        else:
            data[k] = v
    save(data)
    return data
