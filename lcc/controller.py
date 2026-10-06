"""Arayüz, CLI ve servis için ortak üst katman: seçimleri güç kaynağına göre hatırlar."""

from __future__ import annotations

from . import config
from . import hardware as hw
from .backends import detect
from .backends.base import FAN_MODES, Backend, Unsupported


class Controller:
    def __init__(self, backend: Backend | None = None):
        self.backend = backend or detect()
        self.caps = self.backend.capabilities()

    @staticmethod
    def source() -> str:
        return "battery" if hw.on_battery() else "ac"

    def desired(self, source: str | None = None) -> tuple[str, str]:
        conf = config.load()[source or self.source()]
        mode = conf.get("mode")
        fan = conf.get("fan")
        if mode not in self.caps.modes:
            mode = self.caps.modes[0] if self.caps.modes else None
        if self.caps.fan_modes and fan not in self.caps.fan_modes:
            fan = "auto"
        return mode, fan

    def set_mode(self, mode: str) -> tuple[str, str]:
        if mode not in self.caps.modes:
            raise Unsupported(mode)
        src = self.source()
        _, fan = self.desired(src)
        self.backend.apply(mode, fan)
        config.update(**{src: {"mode": mode}})
        return mode, fan

    def next_mode(self) -> tuple[str, str]:
        """Kısayol için: Performans → Eğlence → Sessiz → ... (pil tasarrufu döngüye girmez,
        yalnızca pildeyken eklenir)."""
        cycle = [m for m in ("performance", "balanced", "quiet") if m in self.caps.modes]
        if self.source() == "battery" and "powersave" in self.caps.modes:
            cycle.append("powersave")
        cur, _ = self.backend.current()
        if cur is None:
            cur, _ = self.desired()
        i = cycle.index(cur) if cur in cycle else -1
        return self.set_mode(cycle[(i + 1) % len(cycle)])

    def set_fan(self, fan: str) -> tuple[str, str]:
        if fan not in self.caps.fan_modes or fan not in FAN_MODES:
            raise Unsupported(fan)
        src = self.source()
        mode, _ = self.desired(src)
        self.backend.apply(mode, fan)
        config.update(**{src: {"fan": fan}})
        return mode, fan

    def reapply(self) -> bool:
        """Etkin profil kullanıcının seçimi değilse yeniden uygular. Değiştiyse True."""
        mode, fan = self.desired()
        if mode is None:
            return False
        cur = self.backend.current()
        if cur == (mode, fan) or (not self.caps.fan_modes and cur[0] == mode):
            return False
        self.backend.apply(mode, fan)
        return True
