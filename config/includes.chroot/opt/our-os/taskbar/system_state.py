#!/usr/bin/env python3
"""Real Linux system state for OUR OS.

Backends, in priority order:
  Wi-Fi      : nmcli  (NetworkManager)
  Bluetooth  : bluetoothctl / rfkill
  Audio      : wpctl (PipeWire) → pactl (PulseAudio) fallback
  Battery    : /sys/class/power_supply  (UPower-free, works in VMs)
  Brightness : /sys/class/backlight

Everything is wrapped so a missing tool degrades gracefully to "unknown"
instead of crashing the taskbar.
"""
import os
import re
import shutil
import subprocess
import threading
import time
from typing import Optional

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GObject, GLib  # noqa: E402


def _run(cmd, timeout=2.0):
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        ).stdout
    except Exception:
        return ""


def _has(tool: str) -> bool:
    return shutil.which(tool) is not None


class SystemState(GObject.GObject):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    POLL_SECONDS = 2.0

    def __init__(self):
        super().__init__()
        # Public, read-only-by-convention state.
        self.wifi_on: Optional[bool] = None
        self.wifi_ssid: Optional[str] = None
        self.bluetooth_on: Optional[bool] = None
        self.volume: Optional[int] = None       # 0..100
        self.muted: Optional[bool] = None
        self.brightness: Optional[int] = None   # 0..100
        self.battery_percent: Optional[int] = None
        self.battery_charging: Optional[bool] = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_snapshot = None

    # ---------- lifecycle ----------
    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            snap = self._snapshot()
            if snap != self._last_snapshot:
                self._last_snapshot = snap
                # Emit on the GTK main thread.
                GLib.idle_add(self._apply, snap)
            self._stop.wait(self.POLL_SECONDS)

    def _apply(self, snap):
        (self.wifi_on, self.wifi_ssid, self.bluetooth_on,
         self.volume, self.muted, self.brightness,
         self.battery_percent, self.battery_charging) = snap
        self.emit("changed")
        return False

    # ---------- readers ----------
    def _snapshot(self):
        wifi_on, ssid = self._read_wifi()
        bt = self._read_bluetooth()
        vol, muted = self._read_volume()
        bright = self._read_brightness()
        batt, charging = self._read_battery()
        return (wifi_on, ssid, bt, vol, muted, bright, batt, charging)

    def _read_wifi(self):
        if not _has("nmcli"):
            return None, None
        out = _run(["nmcli", "-t", "-f", "WIFI", "general"])
        if not out.strip():
            return None, None
        on = out.strip().split(":")[-1].lower() == "enabled"
        ssid = None
        if on:
            dev = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION",
                        "device", "status"])
            for line in dev.splitlines():
                parts = line.split(":")
                if len(parts) >= 4 and parts[1] == "wifi" and parts[2] == "connected":
                    ssid = parts[3] or None
                    break
        return on, ssid

    def _read_bluetooth(self):
        if _has("rfkill"):
            out = _run(["rfkill", "list", "bluetooth"])
            if out:
                # "Soft blocked: yes/no"
                m = re.search(r"Soft blocked:\s*(yes|no)", out)
                if m:
                    return m.group(1) == "no"
        if _has("bluetoothctl"):
            out = _run(["bluetoothctl", "show"])
            m = re.search(r"Powered:\s*(yes|no)", out)
            if m:
                return m.group(1) == "yes"
        return None

    def _read_volume(self):
        if _has("wpctl"):
            out = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
            m = re.search(r"Volume:\s*([0-9.]+)", out)
            if m:
                vol = int(round(float(m.group(1)) * 100))
                return vol, "[MUTED]" in out
        if _has("pactl"):
            out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
            m = re.search(r"(\d+)%", out)
            vol = int(m.group(1)) if m else None
            mute = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
            muted = "yes" in mute.lower()
            return vol, muted
        return None, None

    def _read_brightness(self):
        base = "/sys/class/backlight"
        if not os.path.isdir(base):
            return None
        for name in os.listdir(base):
            cur = os.path.join(base, name, "brightness")
            mx = os.path.join(base, name, "max_brightness")
            try:
                with open(cur) as f:
                    c = int(f.read().strip())
                with open(mx) as f:
                    m = int(f.read().strip())
                if m > 0:
                    return int(round(c * 100 / m))
            except Exception:
                continue
        return None

    def _read_battery(self):
        base = "/sys/class/power_supply"
        if not os.path.isdir(base):
            return None, None
        for name in os.listdir(base):
            d = os.path.join(base, name)
            try:
                with open(os.path.join(d, "type")) as f:
                    if f.read().strip() != "Battery":
                        continue
                with open(os.path.join(d, "capacity")) as f:
                    pct = int(f.read().strip())
                charging = None
                try:
                    with open(os.path.join(d, "status")) as f:
                        s = f.read().strip().lower()
                    charging = s in ("charging", "full")
                except Exception:
                    pass
                return pct, charging
            except Exception:
                continue
        return None, None

    # ---------- actuators (real Linux actions) ----------
    def set_wifi(self, on: bool):
        if _has("nmcli"):
            _run(["nmcli", "radio", "wifi", "on" if on else "off"])
            self._kick()

    def set_bluetooth(self, on: bool):
        if _has("rfkill"):
            _run(["rfkill", "unblock" if on else "block", "bluetooth"])
        elif _has("bluetoothctl"):
            _run(["bluetoothctl", "power", "on" if on else "off"])
        self._kick()

    def set_volume(self, percent: int):
        percent = max(0, min(100, int(percent)))
        if _has("wpctl"):
            _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@",
                  f"{percent}%"])
        elif _has("pactl"):
            _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@",
                  f"{percent}%"])
        self._kick()

    def set_muted(self, muted: bool):
        if _has("wpctl"):
            _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@",
                  "1" if muted else "0"])
        elif _has("pactl"):
            _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@",
                  "1" if muted else "0"])
        self._kick()

    def set_brightness(self, percent: int):
        percent = max(0, min(100, int(percent)))
        base = "/sys/class/backlight"
        if not os.path.isdir(base):
            return
        for name in os.listdir(base):
            mx = os.path.join(base, name, "max_brightness")
            cur = os.path.join(base, name, "brightness")
            try:
                with open(mx) as f:
                    m = int(f.read().strip())
                val = int(round(percent * m / 100))
                with open(cur, "w") as f:
                    f.write(str(val))
            except PermissionError:
                # Live ISO autologin user needs a sudoers rule or
                # a small setuid helper. See notes below.
                pass
            except Exception:
                pass
        self._kick()

    def _kick(self):
        """Force an immediate poll instead of waiting POLL_SECONDS."""
        def run():
            snap = self._snapshot()
            self._last_snapshot = snap
            GLib.idle_add(self._apply, snap)
        threading.Thread(target=run, daemon=True).start()