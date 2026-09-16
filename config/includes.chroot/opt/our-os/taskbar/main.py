#!/usr/bin/env python3
"""OUR OS Taskbar — entry point."""
import sys
import signal
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib  # noqa: E402

from taskbar import TaskbarWindow
from system_state import SystemState


def load_css():
    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    provider.load_from_path("/opt/our-os/taskbar/style.css")
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def main():
    load_css()
    state = SystemState()
    state.start()

    win = TaskbarWindow(state)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()

    # Allow Ctrl+C to kill the process cleanly when run from a terminal.
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, Gtk.main_quit)

    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())