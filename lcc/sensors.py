"""Sistem izleme: işlemci, ekran kartı, bellek, disk, pil, fanlar.

Root gerektirmez. Uyuyan ayrı ekran kartını uyandırmamak için kart uykudayken
nvidia-smi çağrılmaz.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field

from . import hardware as hw
from .hardware import read, read_int


@dataclass
class GpuSample:
    name: str
    sleeping: bool
    usage: float | None = None      # %
    temp: float | None = None       # °C
    power: float | None = None      # W
    power_limit: float | None = None    # şu an uygulanan sınır (W)
    clock: float | None = None      # MHz
    power_max: float | None = None      # kartın izin verdiği en yüksek sınır (Dynamic Boost tavanı)


@dataclass
class Snapshot:
    time: float
    cpu_name: str
    cpu_usage: float | None
    cpu_freq: float | None          # MHz, çekirdeklerin en yükseği
    cpu_freq_avg: float | None
    cpu_temp: float | None
    cpu_power_limit: float | None   # W (RAPL PL1)
    cpu_power_limit2: float | None  # W (RAPL PL2)
    gpu: GpuSample | None
    mem_used: float                 # %
    mem_total_gb: float
    disk_used: float                # %
    disk_total_gb: float
    on_battery: bool
    battery: float | None           # %
    battery_power: float | None     # W
    fans: dict[str, float] = field(default_factory=dict)  # ad -> % veya RPM (fan_units)
    fan_units: str = "%"

    def to_dict(self) -> dict:
        return asdict(self)


class Sensors:
    def __init__(self):
        self._prev_stat: tuple[int, int] | None = None
        self._cpu_temp_path = self._find_cpu_temp()
        self._rapl = self._find_rapl()
        self._dgpu = hw.discrete_gpu()
        self._has_nvsmi = shutil.which("nvidia-smi") is not None

    # --- işlemci -----------------------------------------------------------
    @staticmethod
    def _find_cpu_temp() -> str | None:
        for h in glob.glob("/sys/class/hwmon/hwmon*"):
            name = read(h + "/name")
            if name == "coretemp":
                for lbl in glob.glob(h + "/temp*_label"):
                    if read(lbl, "").startswith("Package"):
                        return lbl.replace("_label", "_input")
                return h + "/temp1_input"
            if name in ("k10temp", "zenpower"):
                for lbl in glob.glob(h + "/temp*_label"):
                    if read(lbl) in ("Tctl", "Tdie"):
                        return lbl.replace("_label", "_input")
                return h + "/temp1_input"
        for z in glob.glob("/sys/class/thermal/thermal_zone*"):
            if read(z + "/type") in ("x86_pkg_temp", "cpu-thermal", "cpu_thermal"):
                return z + "/temp"
        return None

    @staticmethod
    def _find_rapl() -> str | None:
        for p in ("/sys/class/powercap/intel-rapl:0", "/sys/class/powercap/intel-rapl-mmio:0"):
            if os.path.exists(p + "/constraint_0_power_limit_uw"):
                return p
        return None

    def _cpu_usage(self) -> float | None:
        try:
            with open("/proc/stat") as f:
                vals = [int(x) for x in f.readline().split()[1:]]
        except OSError:
            return None
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals[:8])
        prev, self._prev_stat = self._prev_stat, (idle, total)
        if prev is None or total == prev[1]:
            return None
        return max(0.0, min(100.0, 100.0 * (1 - (idle - prev[0]) / (total - prev[1]))))

    @staticmethod
    def _cpu_freq() -> tuple[float | None, float | None]:
        freqs = [read_int(p) for p in
                 glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq")]
        freqs = [f for f in freqs if f]
        if not freqs:
            return None, None
        return max(freqs) / 1000, sum(freqs) / len(freqs) / 1000

    # --- ekran kartı -------------------------------------------------------
    def _gpu(self) -> GpuSample | None:
        g = self._dgpu
        if g is None:
            return None
        sleeping = read(g.sysfs + "/power/runtime_status") == "suspended"
        s = GpuSample(name=g.name, sleeping=sleeping)
        if sleeping:
            return s
        if g.vendor == "nvidia" and self._has_nvsmi:
            q = "utilization.gpu,temperature.gpu,power.draw,enforced.power.limit,clocks.gr,power.max_limit"
            try:
                out = subprocess.run(
                    ["nvidia-smi", f"--id={g.pci}", f"--query-gpu={q}",
                     "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=3).stdout.strip()
                vals = [v.strip() for v in out.split(",")]

                def num(v):
                    try:
                        return float(v)
                    except ValueError:
                        return None
                if len(vals) == 6:
                    s.usage, s.temp, s.power, s.power_limit, s.clock, s.power_max = map(num, vals)
            except (OSError, subprocess.SubprocessError):
                pass
        elif g.vendor == "amd":
            s.usage = read_int(g.sysfs + "/gpu_busy_percent")
            for h in glob.glob(g.sysfs + "/hwmon/hwmon*"):
                t = read_int(h + "/temp1_input")
                s.temp = t / 1000 if t is not None else None
                p = read_int(h + "/power1_average") or read_int(h + "/power1_input")
                s.power = p / 1e6 if p else None
        return s

    # --- pil ---------------------------------------------------------------
    @staticmethod
    def _battery() -> tuple[float | None, float | None]:
        bats = hw.batteries()
        if not bats:
            return None, None
        b = bats[0]
        cap = read_int(b + "/capacity")
        pw = read_int(b + "/power_now")
        if pw is None:
            c, v = read_int(b + "/current_now"), read_int(b + "/voltage_now")
            pw = c * v // 1_000_000 if c is not None and v is not None else None
        return (float(cap) if cap is not None else None,
                pw / 1e6 if pw is not None else None)

    # --- fanlar ------------------------------------------------------------
    @staticmethod
    def hwmon_fans() -> dict[str, float]:
        """Genel hwmon fan devirleri (RPM). acpi_fan güvenilmez değerler verdiği için atlanır."""
        fans = {}
        for h in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            name = read(h + "/name", "")
            if name == "acpi_fan":
                continue
            for f in sorted(glob.glob(h + "/fan*_input")):
                rpm = read_int(f)
                if rpm is None or rpm > 20000:
                    continue
                label = read(f.replace("_input", "_label")) or f"{name} {os.path.basename(f)[:4]}"
                fans[label] = float(rpm)
        return fans

    def sample(self) -> Snapshot:
        temp = read_int(self._cpu_temp_path) if self._cpu_temp_path else None
        pl1 = pl2 = None
        if self._rapl:
            v1 = read_int(self._rapl + "/constraint_0_power_limit_uw")
            v2 = read_int(self._rapl + "/constraint_1_power_limit_uw")
            pl1 = v1 / 1e6 if v1 else None
            pl2 = v2 / 1e6 if v2 else None
        fmax, favg = self._cpu_freq()
        mem = {}
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    k, v = line.split(":", 1)
                    mem[k] = int(v.split()[0])
        except OSError:
            pass
        mt = mem.get("MemTotal", 0)
        ma = mem.get("MemAvailable", 0)
        du = shutil.disk_usage("/")
        bat, batp = self._battery()
        fans = self.hwmon_fans()
        return Snapshot(
            time=time.time(),
            cpu_name=hw.cpu_name(),
            cpu_usage=self._cpu_usage(),
            cpu_freq=fmax, cpu_freq_avg=favg,
            cpu_temp=temp / 1000 if temp is not None else None,
            cpu_power_limit=pl1, cpu_power_limit2=pl2,
            gpu=self._gpu(),
            mem_used=100 * (mt - ma) / mt if mt else 0.0,
            mem_total_gb=mt / 1024**2,
            disk_used=100 * du.used / du.total,
            disk_total_gb=du.total / 1e9,
            on_battery=hw.on_battery(),
            battery=bat, battery_power=batp,
            fans=fans, fan_units="rpm" if fans else "%",
        )
