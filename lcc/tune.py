"""Sistem analizi ve optimizasyon: işlemci turbo, performans modu, SSD TRIM, TCP,
DNS, Wi-Fi, fan sürücüsü, servisler ve disk alanı.

Her kontrol bir sonuç sözlüğü döndürür:
    {"id", "state": ok|warn|bad|info, "value": kısa durum, "detail": açıklama,
     "fix": düzeltme mümkünse True}
Düzeltmeler root gerektirince lcc-helper (polkit, wheel'e parolasız) kullanılır.
"""

from __future__ import annotations

import concurrent.futures as cf
import glob
import os
import random
import shutil
import socket
import statistics
import struct
import subprocess
import time
import urllib.request

from . import config, helper
from .i18n import t

HELPER_MIN = 5

# id: (görünen ad, test edilen birincil adres)
DNS_PROVIDERS: dict[str, tuple[str, str]] = {
    "google": ("Google", "8.8.8.8"),
    "cloudflare": ("Cloudflare", "1.1.1.1"),
    "quad9": ("Quad9", "9.9.9.9"),
    "adguard": ("AdGuard", "94.140.14.140"),
    "opendns": ("OpenDNS", "208.67.222.222"),
    "controld": ("Control D", "76.76.2.0"),
}
DNS_TEST_DOMAINS = ["google.com", "youtube.com", "github.com", "wikipedia.org",
                    "trendyol.com", "netflix.com"]
SPEED_URL = "https://speed.cloudflare.com/__down?bytes=25000000"
SPEED_UP_URL = "https://speed.cloudflare.com/__up"
# Cloudflare hız uç noktası Python'un varsayılan User-Agent'ını reddediyor (403).
UA = {"User-Agent": "Mozilla/5.0 laptop-control-center"}


def _read(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def _cmd(*args: str, timeout: float = 5) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def helper_ready() -> bool:
    return helper.installed() and helper.version() >= HELPER_MIN


def _result(id_, state, value, detail, fix=False) -> dict:
    return {"id": id_, "state": state, "value": value, "detail": detail, "fix": bool(fix)}


# --- kontroller ---------------------------------------------------------------------

def _on_battery() -> bool:
    from .hardware import on_battery
    return on_battery()


def check_turbo() -> dict:
    no_turbo = _read("/sys/devices/system/cpu/intel_pstate/no_turbo")
    boost = _read("/sys/devices/system/cpu/cpufreq/boost")
    if no_turbo is None and boost is None:
        return _result("turbo", "info", t("tune.na"), t("tune.turbo.na"))
    on = no_turbo == "0" if no_turbo is not None else boost == "1"
    persistent = os.path.exists("/etc/tmpfiles.d/lcc-turbo.conf")
    mhz = _read("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
    ghz = f"{int(mhz) / 1e6:.1f} GHz" if mhz and mhz.isdigit() else ""
    if not on and config.load()["ac" if not _on_battery() else "battery"]["mode"] in ("quiet", "powersave"):
        return _result("turbo", "ok", t("tune.off"), t("tune.turbo.mode"))
    if not on:
        return _result("turbo", "bad", t("tune.off"), t("tune.turbo.off", ghz=ghz), fix=True)
    if not persistent:
        return _result("turbo", "warn", t("tune.on"), t("tune.turbo.boot"), fix=True)
    return _result("turbo", "ok", t("tune.on"), t("tune.turbo.ok", ghz=ghz))


def check_mode() -> dict:
    conf = config.load()
    mode, boot = conf["ac"]["mode"], conf.get("boot_mode")
    if isinstance(boot, dict):
        boot = boot.get("ac")
    if mode == "performance":
        return _result("mode", "ok", t("mode.performance"), t("tune.mode.ok"))
    if mode == "balanced":
        return _result("mode", "ok", t("mode.balanced"),
                       t("tune.mode.boot") if boot == "balanced" else t("tune.mode.balanced"))
    return _result("mode", "warn", t("mode." + mode), t("tune.mode.low"), fix=True)


def _logind(prop: str) -> str:
    out = _cmd("busctl", "get-property", "org.freedesktop.login1", "/org/freedesktop/login1",
               "org.freedesktop.login1.Manager", prop)
    return out.split(" ", 1)[1].strip('"') if " " in out else ""


def check_sleep() -> dict:
    """Kapak kapanınca (ya da uyku tuşuyla) sistem uyursa çalışan işler durur."""
    lid = _logind("HandleLidSwitch")
    ac = _logind("HandleLidSwitchExternalPower") or lid   # boş: pildeki ayarı izler
    key = _logind("HandleSuspendKey")
    if not lid:
        return _result("sleep", "info", t("tune.na"), t("tune.sleep.na"))
    if lid == "ignore" and ac == "ignore" and key == "ignore":
        return _result("sleep", "ok", t("tune.sleep.never"), t("tune.sleep.ok"))
    return _result("sleep", "bad", t("tune.sleep.lid"), t("tune.sleep.bad"), fix=True)


def check_trim() -> dict:
    enabled = _cmd("systemctl", "is-enabled", "fstrim.timer") == "enabled"
    # Şifreli kök diskte TRIM'in SSD'ye ulaşması için dm-crypt discard'a izin vermeli.
    crypt_ok, crypt_any = True, False
    for dm in glob.glob("/sys/block/dm-*"):
        if (_read(dm + "/dm/uuid") or "").startswith("CRYPT-"):
            crypt_any = True
            if (_read(dm + "/queue/discard_max_bytes") or "0") == "0":
                crypt_ok = False
    pending = crypt_any and not crypt_ok and "allow-discards" in (_read("/etc/default/limine") or "")
    if not enabled:
        return _result("trim", "bad", t("tune.off"), t("tune.trim.off"), fix=True)
    if crypt_any and not crypt_ok:
        return _result("trim", "warn", t("tune.trim.blocked"),
                       t("tune.trim.reboot") if pending else t("tune.trim.crypt"))
    return _result("trim", "ok", t("tune.weekly"), t("tune.trim.ok"))


def check_tcp() -> dict:
    cc = _read("/proc/sys/net/ipv4/tcp_congestion_control") or "?"
    if cc == "bbr":
        return _result("tcp", "ok", "BBR", t("tune.tcp.ok"))
    return _result("tcp", "warn", cc, t("tune.tcp.slow"), fix=True)


def dns_current() -> str:
    """Seçili sağlayıcı kimliği; Kontrol Merkezi ayarlamadıysa 'auto'."""
    raw = _read("/etc/systemd/resolved.conf.d/30-lcc-dns.conf") or ""
    for line in raw.splitlines():
        if line.startswith("# laptop-control-center") and "(" in line:
            return line.split("(", 1)[1].split(")", 1)[0]
    return "auto"


def dns_servers() -> list[str]:
    out = _cmd("resolvectl", "dns")
    servers = []
    for line in out.splitlines():
        if ":" in line:
            servers += [s.split("#")[0] for s in line.split(":", 1)[1].split()]
    return list(dict.fromkeys(servers))


def check_dns(results: dict | None = None) -> dict:
    cur = dns_current()
    name = DNS_PROVIDERS[cur][0] if cur in DNS_PROVIDERS else t("tune.dns.auto")
    if results:
        best = min(results, key=lambda k: results[k]["score"])
        if cur != best and (cur not in results or results[cur]["score"] - results[best]["score"] > 3):
            return _result("dns", "warn", name, t("tune.dns.better", name=results[best]["name"],
                                                  ms=round(results[best]["uncached"])), fix=True)
        return _result("dns", "ok", name, t("tune.dns.best"))
    if cur == "auto":
        return _result("dns", "warn", name, t("tune.dns.untested"), fix=True)
    return _result("dns", "ok", name, t("tune.dns.set"))


def wifi_info() -> dict | None:
    for dev in sorted(glob.glob("/sys/class/net/*/wireless")):
        iface = dev.split("/")[4]
        link = _cmd("iw", "dev", iface, "link")
        if "Connected" not in link:
            continue
        info = {"iface": iface}
        for line in link.splitlines():
            line = line.strip()
            if line.startswith("freq:"):
                info["freq"] = float(line.split()[1])
            elif line.startswith("signal:"):
                info["signal"] = int(float(line.split()[1]))
            elif line.startswith("rx bitrate:"):
                info["rate"] = float(line.split()[2])
        info["powersave"] = "on" in _cmd("iw", "dev", iface, "get", "power_save")
        return info
    return None


def check_wifi(on_battery: bool) -> dict:
    w = wifi_info()
    if not w:
        return _result("wifi", "info", t("tune.wifi.none"), t("tune.wifi.none.hint"))
    band = "5 GHz" if w.get("freq", 0) > 5000 else ("6 GHz" if w.get("freq", 0) > 5900 else "2.4 GHz")
    value = f"{band} · {w.get('signal', '?')} dBm · {int(w.get('rate', 0))} Mbit/s"
    if w["powersave"] and not on_battery:
        return _result("wifi", "warn", value, t("tune.wifi.ps"), fix=True)
    if band == "2.4 GHz":
        return _result("wifi", "warn", value, t("tune.wifi.24"))
    if w.get("signal", 0) < -70:
        return _result("wifi", "warn", value, t("tune.wifi.weak"))
    return _result("wifi", "ok", value, t("tune.wifi.ok"))


def check_fan(backend) -> dict:
    if "tccd" in backend.name:
        return _result("fan", "ok", backend.name, t("tune.fan.ok"))
    if any(os.path.isdir(p) for p in glob.glob("/sys/bus/wmi/devices/ABBC0F6*")):
        return _result("fan", "warn", t("tune.fan.generic"), t("tune.fan.driver"))
    return _result("fan", "info", backend.name, t("tune.fan.bios"))


def check_services() -> dict:
    failed = [ln.split()[0] for ln in _cmd("systemctl", "--failed", "--no-legend", "--plain").splitlines() if ln.strip()]
    failed += [ln.split()[0] for ln in _cmd("systemctl", "--user", "--failed", "--no-legend", "--plain").splitlines() if ln.strip()]
    if failed:
        return _result("services", "warn", str(len(failed)), ", ".join(failed[:4]))
    return _result("services", "ok", "0", t("tune.services.ok"))


def check_disk() -> dict:
    total, used, free = shutil.disk_usage("/")
    pct = used * 100 / total
    value = f"%{pct:.0f} · {free / 1e9:.0f} GB {t('tune.free')}"
    if pct > 90:
        return _result("disk", "bad", value, t("tune.disk.full"))
    if pct > 80:
        return _result("disk", "warn", value, t("tune.disk.low"))
    return _result("disk", "ok", value, t("tune.disk.ok"))


def check_memory() -> dict:
    mem = {}
    for line in (_read("/proc/meminfo") or "").splitlines():
        k, v = line.split(":", 1)
        mem[k] = int(v.split()[0])
    total, avail = mem.get("MemTotal", 1), mem.get("MemAvailable", 0)
    zram = bool(glob.glob("/sys/block/zram*"))
    value = f"{(total - avail) / 1048576:.1f} / {total / 1048576:.0f} GB"
    if avail / total < 0.1:
        return _result("memory", "warn", value, t("tune.mem.low"))
    return _result("memory", "ok", value, t("tune.mem.zram") if zram else t("tune.mem.ok"))


def analyze(backend, on_battery: bool, dns_results: dict | None = None) -> list[dict]:
    return [check_turbo(), check_mode(), check_sleep(), check_fan(backend), check_trim(), check_tcp(),
            check_dns(dns_results), check_wifi(on_battery), check_memory(), check_disk(),
            check_services()]


# --- DNS testi ve hız testi ------------------------------------------------------------

def _dns_query(server: str, name: str, timeout: float = 1.5) -> float | None:
    tid = random.randint(0, 0xFFFF)
    q = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    for part in name.split("."):
        q += bytes([len(part)]) + part.encode()
    q += b"\x00" + struct.pack(">HH", 1, 1)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        start = time.perf_counter()
        s.sendto(q, (server, 53))
        while True:
            data, _ = s.recvfrom(4096)
            if struct.unpack(">H", data[:2])[0] == tid:
                return (time.perf_counter() - start) * 1000
    except OSError:
        return None
    finally:
        s.close()


def _bench_one(ip: str) -> dict:
    cached, uncached, fails = [], [], 0
    for _ in range(2):
        for d in DNS_TEST_DOMAINS:
            for name, bucket in ((d, cached), (f"x{random.randint(0, 10**9)}.{d}", uncached)):
                r = _dns_query(ip, name)
                if r is None:
                    fails += 1
                else:
                    bucket.append(r)
    med = lambda x: statistics.median(x) if x else 9999.0  # noqa: E731
    # Yerel resolved önbelleği tekrarları zaten karşılar; asıl önemli olan önbelleksiz süre.
    return {"cached": med(cached), "uncached": med(uncached), "fails": fails,
            "score": med(uncached) * 0.7 + med(cached) * 0.3 + fails * 200}


def dns_benchmark() -> dict:
    """Sağlayıcıları paralel test eder: {id: {name, cached, uncached, fails, score}}."""
    with cf.ThreadPoolExecutor(len(DNS_PROVIDERS)) as ex:
        futs = {k: ex.submit(_bench_one, ip) for k, (_, ip) in DNS_PROVIDERS.items()}
        out = {k: dict(f.result(), name=DNS_PROVIDERS[k][0]) for k, f in futs.items()}
    return out


def speed_test() -> dict:
    """İndirme/yükleme (Mbit/s) ve gecikme (ms); başarısız ölçüm None."""
    res: dict = {"down": None, "up": None, "ping": None, "time": time.time()}
    try:
        start = time.perf_counter()
        n = 0
        with urllib.request.urlopen(urllib.request.Request(SPEED_URL, headers=UA), timeout=20) as r:
            while chunk := r.read(1 << 16):
                n += len(chunk)
        res["down"] = n * 8 / (time.perf_counter() - start) / 1e6
    except OSError:
        pass
    try:
        body = os.urandom(10_000_000)
        req = urllib.request.Request(SPEED_UP_URL, data=body, method="POST", headers=UA)
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
        res["up"] = len(body) * 8 / (time.perf_counter() - start) / 1e6
    except OSError:
        pass
    pings = []
    for _ in range(5):
        try:
            start = time.perf_counter()
            socket.create_connection(("1.1.1.1", 443), timeout=2).close()
            pings.append((time.perf_counter() - start) * 1000)
        except OSError:
            pass
    res["ping"] = statistics.median(pings) if pings else None
    return res


# --- düzeltmeler -----------------------------------------------------------------------

def _need_helper():
    if not helper_ready():
        raise RuntimeError(t("tune.helper.old"))


def fix(item: str, ctl=None, dns_results: dict | None = None) -> None:
    if item == "turbo":
        _need_helper()
        helper.run("turbo", "on") or _fail(item)
    elif item == "mode":
        boot = config.load().get("boot_mode")
        mode = (boot.get("ac") if isinstance(boot, dict) else boot) or "performance"
        config.update(ac={"mode": mode})
        if ctl is not None:
            from .hardware import on_battery
            if not on_battery():
                ctl.set_mode(mode)
    elif item == "sleep":
        _need_helper()
        helper.run("sleep", "off") or _fail(item)
    elif item == "trim":
        _need_helper()
        helper.run("trim", "on") or _fail(item)
    elif item == "tcp":
        _need_helper()
        helper.run("net-tune", "on") or _fail(item)
    elif item == "dns":
        results = dns_results or dns_benchmark()
        set_dns(min(results, key=lambda k: results[k]["score"]))
    elif item == "wifi":
        _need_helper()
        helper.run("wifi-powersave", "off") or _fail(item)
    else:
        raise ValueError(item)


def _fail(item: str):
    raise RuntimeError(t("tune.fix.failed", item=t("tune." + item)))


def set_dns(provider: str) -> None:
    if provider != "auto" and provider not in DNS_PROVIDERS:
        raise ValueError(provider)
    _need_helper()
    helper.run("dns", provider) or _fail("dns")
