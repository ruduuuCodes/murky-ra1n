#!/usr/bin/env python3
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

HID_APPLE_PATH = "/sys/module/hid_apple/parameters"


def read_sysfs(param):
    path = os.path.join(HID_APPLE_PATH, param)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return None
    return None


def get_keyboard_battery():
    ps_path = "/sys/class/power_supply"
    if os.path.exists(ps_path):
        for dev in os.listdir(ps_path):
            cap_path = os.path.join(ps_path, dev, "capacity")
            if os.path.exists(cap_path):
                name = dev
                model_path = os.path.join(ps_path, dev, "model_name")
                if os.path.exists(model_path):
                    with open(model_path, "r") as mf:
                        name = mf.read().strip()
                if any(w in name.lower() for w in ["magic", "apple", "keyboard"]):
                    with open(cap_path, "r") as cf:
                        return f"{name}: {cf.read().strip()}%"
    try:
        out = subprocess.check_output(["upower", "-e"], text=True)
        for line in out.strip().splitlines():
            if "keyboard" in line.lower():
                dev_info = subprocess.check_output(["upower", "-i", line], text=True)
                for dline in dev_info.splitlines():
                    if "percentage:" in dline:
                        return f"Magic Keyboard: {dline.split(':')[1].strip()}"
    except Exception:
        pass
    return "Connected (Battery via USB or generic)"


class MagicKeyboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Apple Magic Keyboard Utility")
        self.geometry("520x460")
        self.resizable(False, False)
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.create_widgets()
        self.load_current_values()

    def create_widgets(self):
        hf = ttk.Frame(self, padding=15)
        hf.pack(fill="x")
        ttk.Label(
            hf, text="Apple Magic Keyboard Settings", font=("Helvetica", 14, "bold")
        ).pack(anchor="w")
        self.battery_label = ttk.Label(
            hf,
            text=f"Battery: {get_keyboard_battery()}",
            font=("Helvetica", 10, "italic"),
            foreground="#555",
        )
        self.battery_label.pack(anchor="w", pady=(3, 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=15)

        sf = ttk.LabelFrame(self, text=" Kernel Settings (hid_apple) ", padding=15)
        sf.pack(fill="x", padx=15, pady=10)

        ttk.Label(sf, text="Fn Keys Mode:").grid(
            row=0, column=0, sticky="w", pady=6
        )
        self.fnmode_var = tk.StringVar(value="1")
        fn_combo = ttk.Combobox(
            sf,
            textvariable=self.fnmode_var,
            state="readonly",
            values=[
                "1: Media keys default (Press Fn for F1-F12)",
                "2: Standard F1-F12 default (Press Fn for Media)",
            ],
            width=38,
        )
        fn_combo.grid(row=0, column=1, sticky="e", pady=6)

        self.swap_opt_cmd_var = tk.BooleanVar()
        ttk.Checkbutton(
            sf,
            text="Swap Option (Alt) and Command (Super/Windows)",
            variable=self.swap_opt_cmd_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=6)

        self.swap_fn_ctrl_var = tk.BooleanVar()
        ttk.Checkbutton(
            sf,
            text="Swap Fn and Left Control",
            variable=self.swap_fn_ctrl_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        bf = ttk.Frame(sf)
        bf.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(
            bf, text="Apply Temporarily", command=self.apply_runtime
        ).pack(side="left", padx=5)
        ttk.Button(
            bf, text="Save Permanently", command=self.apply_persistent
        ).pack(side="left", padx=5)

        lf = ttk.LabelFrame(
            self, text=" Touch ID / Top-Right Lock Key ", padding=15
        )
        lf.pack(fill="x", padx=15, pady=5)
        ttk.Label(
            lf,
            text="Touch ID fingerprint reading requires an Apple Silicon M-series chip.\nYou can remap this sensor button to lock your Linux desktop instead:",
            wraplength=480,
            justify="left",
        ).pack(anchor="w")
        ttk.Button(
            lf, text="How to Bind Lock Screen Shortcut", command=self.lock_info
        ).pack(anchor="w", pady=(8, 0))

    def load_current_values(self):
        val = read_sysfs("fnmode")
        self.fnmode_var.set(
            "2: Standard F1-F12 default (Press Fn for Media)"
            if val == "2"
            else "1: Media keys default (Press Fn for F1-F12)"
        )
        self.swap_opt_cmd_var.set(read_sysfs("swap_opt_cmd") == "1")
        self.swap_fn_ctrl_var.set(read_sysfs("swap_fn_leftctrl") == "1")

    def get_parsed_values(self):
        fnmode = "2" if self.fnmode_var.get().startswith("2") else "1"
        swap_opt_cmd = "1" if self.swap_opt_cmd_var.get() else "0"
        swap_fn_ctrl = "1" if self.swap_fn_ctrl_var.get() else "0"
        return fnmode, swap_opt_cmd, swap_fn_ctrl

    def apply_runtime(self):
        fnmode, swap_opt_cmd, swap_fn_ctrl = self.get_parsed_values()
        cmd = f"echo {fnmode} > {HID_APPLE_PATH}/fnmode && echo {swap_opt_cmd} > {HID_APPLE_PATH}/swap_opt_cmd && echo {swap_fn_ctrl} > {HID_APPLE_PATH}/swap_fn_leftctrl"
        try:
            subprocess.run(["pkexec", "sh", "-c", cmd], check=True)
            messagebox.showinfo("Success", "Settings applied for current session!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply:\n{e}")

    def apply_persistent(self):
        fnmode, swap_opt_cmd, swap_fn_ctrl = self.get_parsed_values()
        conf = f"options hid_apple fnmode={fnmode} swap_opt_cmd={swap_opt_cmd} swap_fn_leftctrl={swap_fn_ctrl}\n"
        cmd = f'echo "{conf.strip()}" > /etc/modprobe.d/hid_apple.conf && update-initramfs -u'
        try:
            subprocess.run(["pkexec", "sh", "-c", cmd], check=True)
            messagebox.showinfo("Success", "Saved to /etc/modprobe.d/hid_apple.conf!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def lock_info(self):
        messagebox.showinfo(
            "Lock Shortcut",
            "Go to Settings -> Keyboard Shortcuts.\nAdd shortcut for: loginctl lock-session\nPress the Touch ID key when prompted to assign it.",
        )


if __name__ == "__main__":
    if not os.path.exists(HID_APPLE_PATH):
        try:
            subprocess.run(["modprobe", "hid_apple"])
        except Exception:
            pass
    app = MagicKeyboardApp()
    app.mainloop()
