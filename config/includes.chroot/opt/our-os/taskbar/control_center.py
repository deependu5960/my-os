#!/usr/bin/env python3
"""OUR OS Control Center — iPhone-inspired, real Linux backends."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa: E402


TILE_W = 150
TILE_H = 78


class ControlCenter(Gtk.Window):
    def __init__(self, state, parent):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.state = state
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.set_transient_for(parent)
        self.set_name("our-control-center")
        self.set_app_paintable(True)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None and screen.is_composited():
            self.set_visual(visual)

        self._build_ui()
        state.connect("changed", lambda *_: self._refresh())

    # --------------------------------------------------------------
    def _build_ui(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_border_width(18)
        outer.get_style_context().add_class("cc-root")
        self.add(outer)

        title = Gtk.Label(label="OUR CONTROL")
        title.get_style_context().add_class("cc-title")
        outer.pack_start(title, False, False, 0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        outer.pack_start(grid, False, False, 0)

        self.wifi_tile    = TileButton("Wi-Fi",     "wifi.svg")
        self.bt_tile      = TileButton("Bluetooth", "bluetooth.svg")
        self.vol_slider   = SliderTile("Sound", "audio.svg", 0, 100)
        self.bright_slider = SliderTile("Brightness", "brightness.svg", 0, 100)

        self.wifi_tile.connect("clicked", lambda *_: self._toggle_wifi())
        self.bt_tile.connect("clicked",   lambda *_: self._toggle_bt())
        self.vol_slider.connect("value-changed",
                                lambda w: self.state.set_volume(int(w.get_value())))
        self.bright_slider.connect("value-changed",
                                   lambda w: self.state.set_brightness(int(w.get_value())))

        grid.attach(self.wifi_tile,      0, 0, 1, 1)
        grid.attach(self.bt_tile,        1, 0, 1, 1)
        grid.attach(self.vol_slider,     0, 1, 1, 1)
        grid.attach(self.bright_slider,  1, 1, 1, 1)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.battery_label = Gtk.Label(label="Battery —")
        self.battery_label.get_style_context().add_class("cc-footer")
        settings_btn = Gtk.Button(label="Settings")
        settings_btn.get_style_context().add_class("cc-settings")
        settings_btn.connect("clicked", lambda *_: self._open_settings())
        footer.pack_start(self.battery_label, True, True, 0)
        footer.pack_end(settings_btn, False, False, 0)
        outer.pack_start(footer, False, False, 0)

    # --------------------------------------------------------------
    def toggle_near(self, parent):
        if self.get_visible():
            self.hide()
            return
        self.show_all()
        self._refresh()

        # Position above the taskbar, right-aligned.
        pw = parent.get_window()
        if pw is None:
            return
        px, py, pw_w, pw_h = pw.get_geometry()
        self_w, self_h = self.get_size()
        x = px + pw_w - self_w - 8
        y = py - self_h - 8
        self.move(x, y)

    def _refresh(self):
        s = self.state
        self.wifi_tile.set_state(s.wifi_on, on_text="ON", off_text="OFF")
        self.bt_tile.set_state(s.bluetooth_on, on_text="ON", off_text="OFF")
        if s.volume is not None:
            self.vol_slider.set_value(s.volume)
        if s.brightness is not None:
            self.bright_slider.set_value(s.brightness)
        if s.battery_percent is not None:
            suffix = " ⚡" if s.battery_charging else ""
            self.battery_label.set_text(f"Battery {s.battery_percent}%{suffix}")

    def _toggle_wifi(self):
        self.state.set_wifi(not bool(self.state.wifi_on))

    def _toggle_bt(self):
        self.state.set_bluetooth(not bool(self.state.bluetooth_on))

    def _open_settings(self):
        import subprocess
        try:
            subprocess.Popen(["our-os-settings"])
        except FileNotFoundError:
            subprocess.Popen(["gnome-control-center"])


# ------------------------------------------------------------------
class TileButton(Gtk.Button):
    def __init__(self, label, icon_file):
        super().__init__()
        self.set_size_request(TILE_W, TILE_H)
        self.get_style_context().add_class("cc-tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_halign(Gtk.Align.CENTER)
        self.icon = Gtk.Image.new_from_file(
            f"/usr/local/our-os/taskbar/assets/{icon_file}"
        )
        self.icon.set_pixel_size(22)
        self.state_label = Gtk.Label(label="—")
        self.state_label.get_style_context().add_class("cc-tile-state")
        self.name_label = Gtk.Label(label=label)
        self.name_label.get_style_context().add_class("cc-tile-name")
        box.pack_start(self.icon, False, False, 0)
        box.pack_start(self.name_label, False, False, 0)
        box.pack_start(self.state_label, False, False, 0)
        self.add(box)

    def set_state(self, on, on_text="ON", off_text="OFF"):
        if on is None:
            self.state_label.set_text("—")
            return
        self.state_label.set_text(on_text if on else off_text)


class SliderTile(Gtk.Box):
    def __init__(self, label, icon_file, lo, hi):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_size_request(TILE_W, TILE_H)
        self.get_style_context().add_class("cc-slider")
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        img = Gtk.Image.new_from_file(
            f"/usr/local/our-os/taskbar/assets/{icon_file}"
        )
        img.set_pixel_size(16)
        lbl = Gtk.Label(label=label)
        lbl.get_style_context().add_class("cc-slider-name")
        head.pack_start(img, False, False, 0)
        head.pack_start(lbl, False, False, 0)
        self.pack_start(head, False, False, 0)

        self._scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, lo, hi, 1
        )
        self._scale.set_draw_value(False)
        self._scale.set_size_request(TILE_W - 20, -1)
        self.pack_start(self._scale, False, False, 0)

    def connect(self, *a):
        # Forward to underlying scale for "value-changed"
        return self._scale.connect(*a)

    def set_value(self, v):
        self._scale.set_value(v)