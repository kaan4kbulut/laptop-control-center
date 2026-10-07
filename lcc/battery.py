"""Kalan pil süresi tahmini.

Pilin bildirdiği anlık güç gürültülü; UPower'ın tahmini ise yarım dakikada bir
yenilenir ve yük değişince geç döner. lcc-daemon pildeyken 2 sn'de bir ölçüp iki
ortalama tutar: hızlı (~6 sn) ve yavaş (~60 sn). Yük belirgin değişince (oyun
açıldı, derleme bitti) yavaş ortalama birkaç saniyede yeni düzeye geçer, yoksa sakin
kalır ve süre zıplamaz.

Her mod + tasarruf kademesi için uzun dönem ortalama tüketim öğrenilir. Mod değişince
tahmin bu oranla hemen ölçeklenir, ardından ölçümle düzeltilir. Aynı oranlarla öbür
modlarda kalan süre de hesaplanır.

Canlı tahmin $XDG_RUNTIME_DIR'e, öğrenilenler durum klasörüne yazılır; panel,
pencere ve `lcc status` oradan okur, servis çalışmıyorsa anlık değere dönerler.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path

from . import config
from . import hardware as hw

log = logging.getLogger("lcc.battery")

INTERVAL = 2        # sn
FAST_TAU = 6        # hızlı ortalama
SLOW_TAU = 60       # yavaş ortalama (gösterilen)
CHASE_TAU = 6       # yük değişince yavaşın hızlıya yetişme süresi
JUMP = 0.2          # iki ortalama bu orandan çok ayrışırsa yük değişti say
SETTLE = 30         # mod değişiminden sonra ölçümün oturması
LEARN_TAU = 900     # modun uzun dönem ortalaması
RATIO = (0.5, 2.0)  # modlar arası ölçek sınırı (farklı yüklerde öğrenilmiş olabilir)
FRESH = 10          # bundan eski tahmin kullanılmaz
SAVE_EVERY = 60

LIVE_FILE = Path(os.environ.get("XDG_RUNTIME_DIR") or config.state_dir()) / "lcc-battery.json"
LEARNED_FILE = config.state_dir() / "battery-learned.json"


def _alpha(dt: float, tau: float) -> float:
    return 1 - math.exp(-dt / tau)


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)


class Estimator:
    def __init__(self, backend, level_fn):
        self.backend = backend
        self.level_fn = level_fn      # o anki tasarruf kademesi
        self.learned: dict[str, float] = {}
        try:
            self.learned = {k: float(v) for k, v in json.loads(LEARNED_FILE.read_text()).items()}
        except (OSError, ValueError, AttributeError):
            pass
        self._reset()
        self._saved = time.monotonic()

    def _reset(self) -> None:
        self.fast = self.slow = None
        self.key = self.mode = None
        self.since = self.last = 0.0

    def _state(self) -> tuple[str | None, str]:
        try:
            mode = self.backend.current()[0]
        except Exception:
            mode = self.mode
        return mode, self.level_fn() or "off"

    def _ratio(self, new: str, old: str) -> float | None:
        a, b = self.learned.get(new), self.learned.get(old)
        if not a or not b:
            return None
        return min(max(a / b, RATIO[0]), RATIO[1])

    def tick(self) -> bool:
        try:
            self._tick()
        except Exception:
            log.exception("battery estimate failed")
        return True

    def _tick(self) -> None:
        now = time.monotonic()
        w = hw.battery_watts() if hw.on_battery() else None
        wh = hw.battery_energy()
        if not w or w < 0.5 or wh is None:
            if self.slow is not None:
                self._reset()
                self.save()
                LIVE_FILE.unlink(missing_ok=True)
            return
        mode, level = self._state()
        key = f"{mode}/{level}"
        if self.slow is None:
            self.fast = self.slow = w
            self.key, self.mode, self.since = key, mode, now
        else:
            dt = min(now - self.last, 30)
            if key != self.key:
                r = self._ratio(key, self.key)
                if r:
                    # Ölçüm yetişene kadar öğrenilmiş farkla hemen tahmin et.
                    self.fast *= r
                    self.slow *= r
                log.info("mode %s -> %s, ratio %s", self.key, key, r and round(r, 2))
                self.key, self.mode, self.since = key, mode, now
            self.fast += _alpha(dt, FAST_TAU) * (w - self.fast)
            moved = abs(self.fast - self.slow) > JUMP * self.slow
            tau = CHASE_TAU if moved or now - self.since < SETTLE else SLOW_TAU
            self.slow += _alpha(dt, tau) * (self.fast - self.slow)
            if mode and now - self.since >= SETTLE:
                old = self.learned.get(key)
                self.learned[key] = self.slow if old is None else old + _alpha(dt, LEARN_TAU) * (self.slow - old)
        self.last = now
        _write(LIVE_FILE, {"time": time.time(), "watts": self.slow, "hours": wh / self.slow,
                           "mode": mode, "modes": self._per_mode(wh, level)})
        if now - self._saved > SAVE_EVERY:
            self.save()

    def _per_mode(self, wh: float, level: str) -> dict[str, float]:
        """Aynı yük ve kademede öbür modlarda kalan süre (öğrenilmiş olanlar)."""
        out = {self.mode: wh / self.slow}
        for k in self.learned:
            m, lv = k.split("/", 1)
            if lv == level and m != self.mode:
                r = self._ratio(k, self.key)
                if r:
                    out[m] = wh / (self.slow * r)
        return out

    def save(self) -> None:
        self._saved = time.monotonic()
        try:
            _write(LEARNED_FILE, {k: round(v, 2) for k, v in self.learned.items()})
        except OSError as e:
            log.warning("cannot save learned battery rates: %s", e)


def estimate() -> dict | None:
    """Servisin son tahmini: {'watts', 'hours', 'mode', 'modes'}; yoksa ya da eskiyse None."""
    try:
        est = json.loads(LIVE_FILE.read_text())
    except (OSError, ValueError):
        return None
    if time.time() - est.get("time", 0) > FRESH or not hw.on_battery():
        return None
    return est


def hours(watts) -> float | None:
    """Kalan süre: servisin tahmini, yoksa anlık tüketimle."""
    est = estimate()
    if est:
        return est["hours"]
    return hw.battery_hours(watts) if hw.on_battery() else None
