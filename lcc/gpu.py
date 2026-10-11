"""NVIDIA ekran kartı sınırları: modlara göre güç sınırı ve saat tavanı (nvidia-smi).

Alt saat sınırı en düşükte kalır; kart boşta düşük güçte durur, yük gelince modun
tavanına kadar yükselir. nvidia-smi kartı uykudan uyandırdığı için yalnızca mod
değişince (ya da açılıştan sonra ilk kez) çalıştırılır; uygulanan durum kaydedilir.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess

from . import config, helper
from .power import _boot_id

log = logging.getLogger("lcc.gpu")
HELPER_MIN = 6
STATE = "gpu.json"


def available() -> bool:
    return (shutil.which("nvidia-smi") is not None and helper.installed()
            and helper.version() >= HELPER_MIN)


def _state() -> dict:
    try:
        return json.loads((config.state_dir() / STATE).read_text())
    except (OSError, ValueError):
        return {}


def _save(st: dict) -> None:
    p = config.state_dir() / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, indent=2))


def _info(st: dict) -> dict | None:
    """En yüksek saat ve güç sınırları; bir kez okunup saklanır."""
    if st.get("info"):
        return st["info"]
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=clocks.max.gr,power.default_limit,power.max_limit",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        clock, default, top = (float(v) for v in out.strip().splitlines()[0].split(","))
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None
    st["info"] = {"clock": int(clock), "default": default, "max": top}
    return st["info"]


def limits(mode: str, info: dict) -> tuple[str, str]:
    """(saat tavanı MHz | reset, güç sınırı W) — config'teki yüzdelerden."""
    clock_pct, power_pct = config.load().get("gpu_limit", {}).get(mode, [100, 100])
    clock = "reset" if clock_pct >= 100 else str(info["clock"] * clock_pct // 100)
    power = info["max"] if power_pct == "max" else info["default"] * power_pct / 100
    return clock, str(int(min(max(power, 5), info["max"])))


def apply(mode: str, force: bool = False) -> bool:
    if not available() or mode is None:
        return False
    st = _state()
    if not force and st.get("mode") == mode and st.get("boot") == _boot_id():
        return False
    info = _info(st)
    if not info:
        return False
    clock, power = limits(mode, info)
    if not helper.run("gpu", clock, power):
        return False
    log.info("gpu %s: clock %s, power %s W", mode, clock, power)
    st.update(mode=mode, boot=_boot_id())
    _save(st)
    return True
