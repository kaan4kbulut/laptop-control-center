"""Komut satırı: lcc status | mode | fan | kbd | charge | fnlock | power | setup | monitor | gui | daemon"""

from __future__ import annotations

import argparse
import json
import sys
import time

from gi.repository import GLib

from . import __version__, config
from . import hardware as hw
from .backends.base import FAN_MODES, MODES, KeyboardState, SetupRequired, Unsupported
from .i18n import t


def _fmt(v, unit="", nd=0):
    return "—" if v is None else f"{v:.{nd}f}{unit}"


def _controller():
    from .controller import Controller
    return Controller()


def cmd_status(args) -> int:
    from .sensors import Sensors
    ctl = _controller()
    b = ctl.backend
    b.start_monitoring()
    s = Sensors()
    s.sample()
    time.sleep(0.5)
    snap = s.sample()
    fans = b.fan_speeds()
    b.stop_monitoring()
    mode, fan = b.current()
    kbd = None
    try:
        kbd = b.keyboard()
    except (Unsupported, GLib.Error):
        pass
    start, end = b.charge_thresholds()
    if args.json:
        out = snap.to_dict()
        out.update(backend=b.id, device=hw.dmi().pretty, mode=mode, fan=fan,
                   backend_fans=fans, keyboard=kbd.__dict__ if kbd else None,
                   charge_start=start, charge_end=end,
                   needs_setup=b.needs_setup(),
                   capabilities={"modes": ctl.caps.modes, "fan_modes": ctl.caps.fan_modes})
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    g = snap.gpu
    rows = [
        (t("status.device"), hw.dmi().pretty),
        (t("status.backend"), b.name),
        ("CPU", snap.cpu_name),
        ("GPU", g.name if g else "—"),
        (t("status.power"), t("power.battery") if snap.on_battery else t("power.ac")),
        (t("status.mode"), t("mode." + mode) if mode else "—"),
        (t("status.fan"), t("fan." + fan) if fan else "—"),
        (t("cpu.limit"), f"{_fmt(snap.cpu_power_limit, ' W')} / {_fmt(snap.cpu_power_limit2, ' W')}"),
        (t("cpu.freq"), _fmt(snap.cpu_freq, " MHz")),
        (t("cpu.temp"), _fmt(snap.cpu_temp, " °C")),
        (t("cpu.usage"), _fmt(snap.cpu_usage, " %")),
    ]
    if g:
        rows.append((t("gpu.usage"), t("gpu.sleeping") if g.sleeping else
                     f"{_fmt(g.usage, ' %')} · {_fmt(g.temp, ' °C')} · {_fmt(g.power, ' W', 1)}"))
    for name, v in fans.items():
        rows.append((t("fan.cpu") if name == "cpu" else t("fan.gpu"), _fmt(v, " %")))
    for name, v in snap.fans.items():
        rows.append((name, _fmt(v, " RPM")))
    rows += [
        (t("mem"), f"{snap.mem_used:.0f} % · {snap.mem_total_gb:.0f} GB"),
        (t("disk"), f"{snap.disk_used:.0f} % · {snap.disk_total_gb:.0f} GB"),
    ]
    if snap.battery is not None:
        rows.append((t("power.battery"),
                     f"{snap.battery:.0f} % · {_fmt(snap.battery_power, ' W', 1)}"))
    if kbd:
        rows.append((t("kbd"), f"{kbd.brightness} · {kbd.color}"))
    if end is not None:
        rows.append((t("charge.limit"), f"{start} → {end} %"))
    w = max(len(k) for k, _ in rows)
    for k, v in rows:
        print(f"{k:<{w}}  {v}")
    if b.needs_setup():
        print("\n" + t("setup.needed"), file=sys.stderr)
    return 0


def cmd_mode(args) -> int:
    ctl = _controller()
    if args.mode is None:
        print(ctl.backend.current()[0] or "")
        return 0
    mode, fan = ctl.next_mode() if args.mode == "next" else ctl.set_mode(args.mode)
    print(f"{t('mode.' + mode)} · {t('fan.' + fan) if fan else ''}".rstrip(" ·"))
    if args.notify:
        from .notify import mode_changed
        mode_changed(ctl, mode, fan)
    return 0


def cmd_fan(args) -> int:
    ctl = _controller()
    if args.fan is None:
        print(ctl.backend.current()[1] or "")
        return 0
    mode, fan = ctl.set_fan(args.fan)
    print(f"{t('mode.' + mode)} · {t('fan.' + fan)}")
    return 0


def cmd_kbd(args) -> int:
    ctl = _controller()
    b = ctl.backend
    cur = b.keyboard()
    if args.brightness is None and args.color is None:
        print(f"{cur.brightness} {cur.color}")
        return 0
    if args.brightness is not None:
        mx = ctl.caps.keyboard.brightness_max if ctl.caps.keyboard else 255
        cur.brightness = round(mx * args.brightness / 100) if args.percent else args.brightness
    if args.color is not None:
        c = args.color if args.color.startswith("#") else "#" + args.color
        int(c[1:], 16)
        cur.color = c.lower()
    b.set_keyboard(cur)
    config.update(keyboard={"color": cur.color, "brightness": cur.brightness})
    return 0


def cmd_charge(args) -> int:
    b = _controller().backend
    if args.value is None:
        s, e = b.charge_thresholds()
        print(f"{s} {e}")
        return 0
    b.set_charge_end(args.value)
    return 0


def cmd_fnlock(args) -> int:
    b = _controller().backend
    if args.state is None:
        print("on" if b.fn_lock() else "off")
        return 0
    b.set_fn_lock(args.state == "on")
    return 0


def cmd_setup(args) -> int:
    ctl = _controller()
    ctl.backend.setup()
    print(t("setup.done"))
    ctl.reapply()
    return 0


def cmd_monitor(args) -> int:
    from .sensors import Sensors
    ctl = _controller()
    s = Sensors()
    ctl.backend.start_monitoring()
    try:
        while True:
            snap = s.sample()
            fans = ctl.backend.fan_speeds()
            g = snap.gpu
            gtxt = "zzz" if g and g.sleeping else (
                f"{_fmt(g.usage, '%')} {_fmt(g.temp, '°C')} {_fmt(g.power, 'W', 1)}" if g else "")
            print(f"CPU {_fmt(snap.cpu_freq, 'MHz'):>8} {_fmt(snap.cpu_temp, '°C'):>5} "
                  f"{_fmt(snap.cpu_usage, '%'):>4} PL1 {_fmt(snap.cpu_power_limit, 'W')} | "
                  f"GPU {gtxt} | fan {' '.join(f'{k}:{v:.0f}%' for k, v in fans.items())} | "
                  f"bat {_fmt(snap.battery, '%')} {_fmt(snap.battery_power, 'W', 1)}",
                  flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        ctl.backend.stop_monitoring()


def cmd_gui(args) -> int:
    from .gui.app import main
    return main(args.page)


def cmd_power(args) -> int:
    from . import power
    if args.level:
        power.request(args.level)
        print(t("power.requested", level=t("power." + args.level)))
        return 0
    st = power.status()
    try:
        from .controller import Controller
        avail = power.available(Controller().backend)
    except Exception:
        avail = power.available()
    print(f"{t('power.title')}: {t('power.' + st['level'])}  ({t('power.request')}: {t('power.' + st['requested'])})")
    for f in power.FEATURES:
        mark = "●" if f in st["active"] else ("○" if avail.get(f) else "–")
        print(f"  {mark} {t('power.f.' + f)}")
    if st["failed"]:
        print(t("power.failed") + ": " + ", ".join(st["failed"]))
    return 0


def cmd_daemon(args) -> int:
    from .daemon import main
    main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lcc", description="laptop-control-center")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("status", help="donanım ve durum özeti / hardware and state summary")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("mode", help="performans modu / performance mode")
    s.add_argument("mode", nargs="?", choices=list(MODES) + ["next"])
    s.add_argument("--notify", action="store_true", help="ekran bildirimi göster / show OSD")
    s.set_defaults(func=cmd_mode)

    s = sub.add_parser("fan", help="fan modu / fan mode")
    s.add_argument("fan", nargs="?", choices=FAN_MODES)
    s.set_defaults(func=cmd_fan)

    s = sub.add_parser("kbd", help="klavye ışığı / keyboard backlight")
    s.add_argument("-b", "--brightness", type=int)
    s.add_argument("-p", "--percent", action="store_true", help="parlaklık yüzde olarak")
    s.add_argument("-c", "--color", help="#rrggbb")
    s.set_defaults(func=cmd_kbd)

    s = sub.add_parser("charge", help="şarj sınırı / charge limit")
    s.add_argument("value", nargs="?", type=int)
    s.set_defaults(func=cmd_charge)

    s = sub.add_parser("fnlock", help="Fn kilidi / Fn lock")
    s.add_argument("state", nargs="?", choices=["on", "off"])
    s.set_defaults(func=cmd_fnlock)

    s = sub.add_parser("setup", help="bir kerelik kurulum (root) / one-time setup (root)")
    s.set_defaults(func=cmd_setup)

    s = sub.add_parser("monitor", help="canlı izleme / live monitor")
    s.add_argument("-i", "--interval", type=float, default=1.0)
    s.set_defaults(func=cmd_monitor)

    s = sub.add_parser("gui", help="ana pencere / main window")
    s.add_argument("page", nargs="?", default="monitor", choices=["monitor", "led", "settings", "power"])
    s.set_defaults(func=cmd_gui)

    s = sub.add_parser("power", help="pil tasarrufu / power saving")
    s.add_argument("level", nargs="?", choices=["auto", "off", "saver", "ultra"])
    s.set_defaults(func=cmd_power)

    s = sub.add_parser("daemon", help="arka plan servisi / background service")
    s.set_defaults(func=cmd_daemon)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        args = build_parser().parse_args(["status"])
    try:
        return args.func(args)
    except SetupRequired as e:
        print(str(e), file=sys.stderr)
        return 3
    except Unsupported as e:
        print(f"{t('unsupported')}{': ' + str(e) if str(e) else ''}", file=sys.stderr)
        return 2
    except GLib.Error as e:
        print(f"DBus: {e.message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
