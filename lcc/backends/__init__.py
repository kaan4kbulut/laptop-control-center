"""Donanıma uygun arka ucu seçer."""

from __future__ import annotations

import os

from .base import Backend
from .generic import GenericBackend
from .tccd import TccdBackend

ALL: list[type[Backend]] = [TccdBackend, GenericBackend]


def detect() -> Backend:
    """En yüksek puanı alan arka ucu döndürür. LCC_BACKEND ile zorlanabilir."""
    forced = os.environ.get("LCC_BACKEND")
    if forced:
        for cls in ALL:
            if cls.id == forced:
                return cls()
        raise SystemExit(f"unknown backend: {forced}")
    best = max(ALL, key=lambda c: c.probe())
    return best()
