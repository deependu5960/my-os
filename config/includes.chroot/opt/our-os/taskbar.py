#!/usr/bin/env python3

import tkinter as tk
import subprocess
import datetime
import os


class OurOSTaskbar:
    def __init__(self):
        self.root = tk.Tk()

        self.root.title("OUR OS Taskbar")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        self.height = 58

        self.root.geometry(
            f"{screen_width}x{self.height}+0+{screen_height - self.height}"
        )

        self.root.configure(bg="#111111")

        # Prevent the window from being minimized/hidden by normal desktop actions.
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.build_ui()

        self.update_clock()

    def build_ui(self):
        # Main taskbar
        bar = tk.Frame(
            self.root,
            bg="#111111",
            height=self.height
        )
        bar.pack(fill="both", expand=True)

        # Left section
        left = tk.Frame(
            bar,
            bg="#111111"
        )
        left.pack(side="left", fill="y")

        start_button = tk.Button(
            left,
            text="●",
            font=("Arial", 20),
            fg="white",
            bg="#111111",
            activebackground="#222222",
            activeforeground="white",
            bd=0,
            width=3,
            command=self.open_launcher
        )

        start_button.pack(
            side="left",
            padx=10
        )

        # Center section
        center = tk.Frame(
            bar,
            bg="#111111"
        )
        center.place(
            relx=0.5,
            rely=0.5,
            anchor="center"
        )

        apps = [
            ("▣", self.open_terminal),
            ("■", self.open_files),
            ("●", self.open_browser),
        ]

        for icon, command in apps:
            button = tk.Button(
                center,
                text=icon,
                font=("Arial", 18),
                fg="white",
                bg="#111111",
                activebackground="#333333",
                activeforeground="white",
                bd=0,
                width=3,
                command=command
            )

            button.pack(
                side="left",
                padx=3
            )

        # Right section
        right = tk.Frame(
            bar,
            bg="#111111"
        )
        right.pack(
            side="right",
            fill="y"
        )

        self.status = tk.Label(
            right,
            text="Wi-Fi   🔊   🔋",
            font=("Arial", 11),
            fg="white",
            bg="#111111"
        )

        self.status.pack(
            side="left",
            padx=12
        )

        self.clock = tk.Label(
            right,
            text="",
            font=("Arial", 10),
            fg="white",
            bg="#111111"
        )

        self.clock.pack(
            side="left",
            padx=12
        )

        control_button = tk.Button(
            right,
            text="⚙",
            font=("Arial", 16),
            fg="white",
            bg="#111111",
            activebackground="#333333",
            activeforeground="white",
            bd=0,
            command=self.open_control_center
        )

        control_button.pack(
            side="left",
            padx=8
        )

    def update_clock(self):
        now = datetime.datetime.now()

        self.clock.config(
            text=now.strftime("%d %b  %H:%M")
        )

        self.root.after(
            1000,
            self.update_clock
        )

    def open_launcher(self):
        try:
            subprocess.Popen(
                ["xfce4-appfinder"]
            )
        except Exception:
            pass

    def open_terminal(self):
        try:
            subprocess.Popen(
                ["xfce4-terminal"]
            )
        except Exception:
            pass

    def open_files(self):
        try:
            subprocess.Popen(
                ["thunar"]
            )
        except Exception:
            pass

    def open_browser(self):
        try:
            subprocess.Popen(
                ["xdg-open", "https://www.google.com"]
            )
        except Exception:
            pass

    def open_control_center(self):
        try:
            subprocess.Popen(
                ["xfce4-settings-manager"]
            )
        except Exception:
            pass

    def close(self):
        self.root.destroy()


if __name__ == "__main__":
    app = OurOSTaskbar()
    app.root.mainloop()