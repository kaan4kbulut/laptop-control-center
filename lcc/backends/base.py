"""Arka uç arayüzü. Her donanım ailesi (Clevo/Tuxedo, genel Linux, ileride ASUS/Lenovo)
bunu uygular; arayüz ve CLI yalnızca bu sınıfı görür."""

from __future__ import annotations

from dataclasses import dataclass, field

# Ortak mod ve fan kimlikleri. Arka uç desteklediklerini döndürür.
MODES = ("performance", "balanced", "quiet", "powersave")
FAN_MODES = ("auto", "silent", "max", "custom")


class Unsupported(Exception):
    """Bu cihaz veya arka uç bu özelliği desteklemiyor."""


class SetupRequired(Exception):
    """Özellik, bir kerelik root kurulumu (`lcc setup`) gerektiriyor."""


@dataclass
class KeyboardCaps:
    brightness_max: int = 0
    color: bool = False
    zones: int = 1


@dataclass
class KeyboardState:
    brightness: int = 0          # 0..brightness_max
    color: str = "#ffffff"       # #rrggbb


@dataclass
class Capabilities:
    modes: list[str] = field(default_factory=list)
    fan_modes: list[str] = field(default_factory=list)
    keyboard: KeyboardCaps | None = None
    charge_end: list[int] = field(default_factory=list)    # izin verilen şarj sınırları
    charge_start: list[int] = field(default_factory=list)
    fn_lock: bool = False


class Backend:
    id = "base"
    name = "Base"

    @classmethod
    def probe(cls) -> int:
        """0: kullanılamaz; daha yüksek puan daha özel arka uç demektir."""
        return 0

    def capabilities(self) -> Capabilities:
        return Capabilities()

    # --- mod + fan ---------------------------------------------------------
    def current(self) -> tuple[str | None, str | None]:
        """(mod, fan) — bilinmiyorsa None."""
        return None, None

    def apply(self, mode: str, fan: str, force: bool = False) -> None:
        raise Unsupported

    def needs_setup(self) -> bool:
        return False

    def setup(self, custom_curve: list[list[int]] | None = None) -> None:
        """Bir kerelik root gerektiren kurulum (ör. tccd profilleri)."""

    # --- izleme ------------------------------------------------------------
    def start_monitoring(self) -> None:
        pass

    def stop_monitoring(self) -> None:
        pass

    def fan_speeds(self) -> dict[str, float]:
        """Fan adı -> yüzde. Desteklenmiyorsa boş."""
        return {}

    # --- klavye ------------------------------------------------------------
    def keyboard(self) -> KeyboardState:
        raise Unsupported

    def set_keyboard(self, state: KeyboardState) -> None:
        raise Unsupported

    # --- şarj --------------------------------------------------------------
    def charge_thresholds(self) -> tuple[int | None, int | None]:
        return None, None

    def set_charge_end(self, value: int) -> None:
        raise Unsupported

    # --- Fn kilidi ---------------------------------------------------------
    def fn_lock(self) -> bool:
        raise Unsupported

    def set_fn_lock(self, on: bool) -> None:
        raise Unsupported
