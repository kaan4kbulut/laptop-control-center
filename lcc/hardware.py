"""Donanım bilgisi: DMI, işlemci/ekran kartı adları, güç kaynağı."""

from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache


def read(path: str, default: str | None = None) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default


def read_int(path: str, default: int | None = None) -> int | None:
    v = read(path)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


@dataclass
class GpuDevice:
    pci: str            # 0000:01:00.0
    vendor: str         # nvidia | amd | intel | other
    name: str
    discrete: bool
    sysfs: str = field(repr=False, default="")


@dataclass
class Dmi:
    sys_vendor: str
    product_name: str
    board_vendor: str
    board_name: str
    product_family: str

    @property
    def pretty(self) -> str:
        v = self.sys_vendor.strip()
        p = self.product_name.strip()
        return p if p.lower().startswith(v.lower()) else f"{v} {p}".strip()


@lru_cache(maxsize=1)
def dmi() -> Dmi:
    b = "/sys/class/dmi/id/"
    return Dmi(*(read(b + k, "") for k in
                 ("sys_vendor", "product_name", "board_vendor", "board_name", "product_family")))


@lru_cache(maxsize=1)
def cpu_name() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    name = line.split(":", 1)[1].strip()
                    return re.sub(r"\s+", " ", name.replace("(R)", "®").replace("(TM)", "™"))
    except OSError:
        pass
    return "CPU"


_VENDORS = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}


def _lspci_names() -> dict[str, str]:
    if not shutil.which("lspci"):
        return {}
    try:
        out = subprocess.run(["lspci", "-D", "-mm"], capture_output=True, text=True,
                             timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    names = {}
    for line in out.splitlines():
        parts = re.findall(r'"([^"]*)"|(\S+)', line)
        fields = [a or b for a, b in parts]
        if len(fields) >= 4:
            names[fields[0]] = fields[3]
    return names


def _nvidia_marketing_name() -> str | None:
    """lspci kod adı verir (GB205M); nvidia-smi gerçek adı. Uyuyan kartı uyandırmamak için
    yalnızca kart zaten uyanıkken çağrılır."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return out.splitlines()[0] if out else None
    except (OSError, subprocess.SubprocessError):
        return None


@lru_cache(maxsize=1)
def gpus() -> list[GpuDevice]:
    names = _lspci_names()
    result = []
    for dev in sorted(glob.glob("/sys/bus/pci/devices/*")):
        cls = read(dev + "/class", "")
        if not cls.startswith("0x03"):
            continue
        pci = os.path.basename(dev)
        vendor = _VENDORS.get(read(dev + "/vendor", ""), "other")
        if vendor == "nvidia":
            discrete = True
        elif vendor == "amd":
            # APU'nun ayrılmış belleği küçüktür; ayrı kartın VRAM'i birkaç GB.
            vram = read_int(dev + "/mem_info_vram_total", 0) or 0
            discrete = vram > 2 * 1024**3
        else:
            discrete = False
        name = names.get(pci, f"{vendor.upper()} GPU")
        if vendor == "nvidia" and read(dev + "/power/runtime_status") != "suspended":
            name = _nvidia_marketing_name() or name
        result.append(GpuDevice(pci, vendor, name, discrete, dev))
    return result


def discrete_gpu() -> GpuDevice | None:
    return next((g for g in gpus() if g.discrete), None)


def on_battery() -> bool:
    """Prize takılı bir 'Mains' kaynağı yoksa ve pil varsa True."""
    mains = [p for p in glob.glob("/sys/class/power_supply/*")
             if read(p + "/type") == "Mains"]
    if mains:
        return not any(read_int(p + "/online") == 1 for p in mains)
    bats = batteries()
    return bool(bats) and read(bats[0] + "/status") == "Discharging"


def batteries() -> list[str]:
    return [p for p in sorted(glob.glob("/sys/class/power_supply/*"))
            if read(p + "/type") == "Battery" and read(p + "/scope", "System") != "Device"]
