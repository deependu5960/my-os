#!/usr/bin/env python3

"""OUR OS Taskbar — a real X11 dock with struts."""

import subprocess

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk, GLib  # noqa: E402

from control_center import ControlCenter


TASKBAR_HEIGHT = 48


class TaskbarWindow(Gtk.Window):

    def __init__(self, state):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.state = state
        self.control_center = None

        # ---- Window-manager contract: this is a dock, not an app ----

        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.stick()

        # ---- RGBA for translucency ----

        screen = self.get_screen()
        visual = screen.get_rgba_visual()

        if visual is not None and screen.is_composited():
            self.set_visual(visual)

        self.set_name("our-os-taskbar")

        self._build_ui()

        # ---- Geometry ----

        self._apply_geometry()

        # React to monitor / resolution changes.
        screen.connect(
            "size-changed",
            lambda *_: self._apply_geometry()
        )

        screen.connect(
            "monitors-changed",
            lambda *_: self._apply_geometry()
        )

        state.connect(
            "changed",
            lambda *_: self._refresh_status()
        )

    # ------------------------------------------------------------------
    # Geometry & struts
    # ------------------------------------------------------------------

    def _target_monitor_geometry(self):
        """Return (x, y, w, h) of the primary monitor in root coords."""

        display = Gdk.Display.get_default()

        monitor = (
            display.get_primary_monitor()
            or display.get_monitor(0)
        )

        g = monitor.get_geometry()

        return g.x, g.y, g.width, g.height

    def _apply_geometry(self):

        x, y, w, h = self._target_monitor_geometry()

        bar_y = y + h - TASKBAR_HEIGHT

        # Size and position.
        self.set_default_size(
            w,
            TASKBAR_HEIGHT
        )

        self.resize(
            w,
            TASKBAR_HEIGHT
        )

        self.move(
            x,
            bar_y
        )

        # If already mapped, push the new geometry to the WM.
        gdk_win = self.get_window()

        if gdk_win is not None:

            gdk_win.move_resize(
                x,
                bar_y,
                w,
                TASKBAR_HEIGHT
            )

            self._set_struts(
                x,
                bar_y,
                w,
                h
            )

    def _set_struts(self, x, y, w, screen_h):
        """
        Temporarily skip X11 strut publishing.

        The current GTK/GDK X11 binding does not expose
        property_change(), which caused the previous crash.

        The taskbar itself remains a real DOCK window.

        Proper _NET_WM_STRUT_PARTIAL support will be added
        separately after the visual taskbar is finalized.
        """

        return

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):

        root = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=0
        )

        root.get_style_context().add_class(
            "taskbar-root"
        )

        self.add(root)

        # ---- LEFT: launcher ----

        left = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        left.get_style_context().add_class(
            "zone-left"
        )

        launcher = Gtk.Button()

        launcher.get_style_context().add_class(
            "launcher-button"
        )

        launcher.set_relief(
            Gtk.ReliefStyle.NONE
        )

        launcher.set_tooltip_text(
            "OUR OS"
        )

        logo = Gtk.Image.new_from_file(
            "/opt/our-os/taskbar/assets/our-logo.svg"
        )

        logo.set_pixel_size(26)

        logo.set_halign(Gtk.Align.CENTER)
        logo.set_valign(Gtk.Align.CENTER)

        launcher.add(logo)

        launcher.connect(
            "clicked",
            self._on_launcher_clicked
        )

        left.pack_start(
            launcher,
            False,
            False,
            0
        )

        root.pack_start(
            left,
            False,
            False,
            8
        )

        # ---- CENTER: pinned + running ----

        center = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6
        )

        center.get_style_context().add_class(
            "zone-center"
        )

        center.set_halign(
            Gtk.Align.CENTER
        )

        self.center_box = center

        for label, cmd in (
            ("Files", "thunar"),
            ("Browser", "firefox-esr"),
            ("Terminal", "x-terminal-emulator"),
        ):

            center.pack_start(
                self._make_app_button(
                    label,
                    cmd
                ),
                False,
                False,
                0
            )

        root.pack_start(
            center,
            True,
            True,
            0
        )

        # ---- RIGHT: status area ----

        right = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8
        )

        right.get_style_context().add_class(
            "zone-right"
        )

        self.wifi_icon = self._status_icon(
            "wifi.svg"
        )

        self.bt_icon = self._status_icon(
            "bluetooth.svg"
        )

        self.audio_icon = self._status_icon(
            "audio.svg"
        )

        self.battery_icon = self._status_icon(
            "battery.svg"
        )

        self.clock = Gtk.Label(
            label="--:--"
        )

        self.clock.get_style_context().add_class(
            "clock"
        )

        GLib.timeout_add_seconds(
            1,
            self._tick_clock
        )

        self._tick_clock()

        for widget in (
            self.wifi_icon,
            self.bt_icon,
            self.audio_icon,
            self.battery_icon,
            self.clock
        ):

            right.pack_start(
                widget,
                False,
                False,
                0
            )

        # The whole right zone is the Control Center trigger.

        clickable = Gtk.EventBox()

        clickable.add(right)

        clickable.connect(
            "button-press-event",
            self._on_status_clicked
        )

        root.pack_end(
            clickable,
            False,
            False,
            8
        )

        self._refresh_status()

    # ------------------------------------------------------------------
    # Application buttons
    # ------------------------------------------------------------------

    def _make_app_button(self, label, cmd):

        btn = Gtk.Button()

        btn.get_style_context().add_class(
            "app-button"
        )

        btn.set_relief(
            Gtk.ReliefStyle.NONE
        )

        btn.set_tooltip_text(
            label
        )

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2
        )

        dot = Gtk.DrawingArea()

        dot.set_size_request(
            6,
            6
        )

        dot.get_style_context().add_class(
            "running-dot"
        )

        lbl = Gtk.Label(
            label=label
        )

        box.pack_start(
            dot,
            False,
            False,
            0
        )

        box.pack_start(
            lbl,
            False,
            False,
            0
        )

        btn.add(box)

        btn.connect(
            "clicked",
            lambda *_: self._launch(cmd)
        )

        return btn

    # ------------------------------------------------------------------
    # Status icons
    # ------------------------------------------------------------------

    def _status_icon(self, filename):

        img = Gtk.Image.new_from_file(
            f"/opt/our-os/taskbar/assets/{filename}"
        )

        # All status icons use the same requested size.
        img.set_pixel_size(20)

        img.set_halign(
            Gtk.Align.CENTER
        )

        img.set_valign(
            Gtk.Align.CENTER
        )

        img.get_style_context().add_class(
            "status-icon"
        )

        return img

    # ------------------------------------------------------------------
    # Behavior
    # ------------------------------------------------------------------

    def _tick_clock(self):

        from datetime import datetime

        self.clock.set_text(
            datetime.now().strftime("%H:%M")
        )

        return True

    def _launch(self, cmd):

        try:

            subprocess.Popen(
                [cmd]
            )

        except FileNotFoundError:

            subprocess.Popen(
                ["xdg-open", cmd]
            )

    def _on_launcher_clicked(self, _btn):

        # Placeholder — later this opens the OUR OS app grid.
        pass

    def _on_status_clicked(self, _widget, _event):

        if self.control_center is None:

            self.control_center = ControlCenter(
                self.state,
                self
            )

            self.control_center.connect(
                "destroy",
                lambda *_: setattr(
                    self,
                    "control_center",
                    None
                )
            )

        self.control_center.toggle_near(
            self
        )

        return True

    # ------------------------------------------------------------------
    # System status
    # ------------------------------------------------------------------

    def _refresh_status(self):

        s = self.state

        # ---- Wi-Fi ----

        if s.wifi_on is True:

            self._swap_icon(
                self.wifi_icon,
                "wifi.svg"
            )

        elif s.wifi_on is False:

            self._swap_icon(
                self.wifi_icon,
                "wifi-off.svg"
            )

        else:

            self._swap_icon(
                self.wifi_icon,
                "wifi-off.svg"
            )

        if s.wifi_on is not None:

            if s.wifi_on:

                if s.wifi_ssid:

                    self.wifi_icon.set_tooltip_text(
                        f"Wi-Fi: on ({s.wifi_ssid})"
                    )

                else:

                    self.wifi_icon.set_tooltip_text(
                        "Wi-Fi: on"
                    )

            else:

                self.wifi_icon.set_tooltip_text(
                    "Wi-Fi: off"
                )

        else:

            self.wifi_icon.set_tooltip_text(
                "Wi-Fi: unknown"
            )

        # ---- Bluetooth ----

        if s.bluetooth_on is True:

            self._swap_icon(
                self.bt_icon,
                "bluetooth.svg"
            )

        elif s.bluetooth_on is False:

            self._swap_icon(
                self.bt_icon,
                "bluetooth-off.svg"
            )

        else:

            self._swap_icon(
                self.bt_icon,
                "bluetooth-off.svg"
            )

        # ---- Audio ----

        if s.muted is True:

            self._swap_icon(
                self.audio_icon,
                "audio-muted.svg"
            )

        else:

            self._swap_icon(
                self.audio_icon,
                "audio.svg"
            )

        # ---- Battery ----

        if s.battery_percent is not None:

            self.battery_icon.set_visible(
                True
            )

            if s.battery_charging:

                self._swap_icon(
                    self.battery_icon,
                    "battery-charging.svg"
                )

            else:

                self._swap_icon(
                    self.battery_icon,
                    "battery.svg"
                )

            self.battery_icon.set_tooltip_text(
                f"Battery: {s.battery_percent}%"
            )

        else:

            self.battery_icon.set_visible(
                False
            )

        return False

    # ------------------------------------------------------------------
    # Icon replacement
    # ------------------------------------------------------------------

    def _swap_icon(self, img, filename):

        img.set_from_file(
            f"/opt/our-os/taskbar/assets/{filename}"
        )

        # IMPORTANT:
        # Do not reset this to 16px.
        # _status_icon() uses 20px and every replacement
        # must keep the same size.

        img.set_pixel_size(20)

        img.set_halign(
            Gtk.Align.CENTER
        )

        img.set_valign(
            Gtk.Align.CENTER
        )