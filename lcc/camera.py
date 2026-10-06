"""Dahili kamera: USB görüntü sınıfı (0e) arayüzlerinin uvcvideo'ya bağlı olup olmadığı.

Okumak root gerektirmez; açıp kapatmak lcc-helper ile yapılır. Kapatınca kamera
sistemden kaybolur (uygulamalar göremez), açınca geri gelir.
"""

from __future__ import annotations

import glob
import os

from . import helper


def _interfaces() -> list[str]:
    out = []
    for intf in glob.glob("/sys/bus/usb/devices/*:*"):
        try:
            with open(intf + "/bInterfaceClass") as f:
                if f.read().strip() == "0e":
                    out.append(intf)
        except OSError:
            continue
    return out


def available() -> bool:
    return bool(_interfaces()) and helper.installed() and helper.version() >= 2


def enabled() -> bool | None:
    intfs = _interfaces()
    if not intfs:
        return None
    return any(os.path.basename(os.path.realpath(i + "/driver")) == "uvcvideo"
               for i in intfs if os.path.exists(i + "/driver"))


def set_enabled(on: bool) -> bool:
    return helper.run("camera", "on" if on else "off")
