# findInCurrentFile-editor.py  ←  THIS ONE WORKS 100%
import os
from pathlib import Path
import tkinter as tk
from tkinter import Listbox, Scrollbar, Button, Label, Frame, END, messagebox

try:
    import json5
except ImportError:
    messagebox.showerror("Missing json5", "Run once:\n    pip install json5")
    raise

# This is the real key used by the extension today
EXTENSION_ID = "findInCurrentFile"

def get_vscode_settings_path() -> Path | None:
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    candidates = [
        Path(appdata) / "Code" / "User" / "settings.json",
        Path(appdata) / "Code - cInsiders" / "User" / "settings.json",
        Path(appdata) / "VSCodium" / "User" / "settings.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def load_settings_jsonc(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json5.load(f), None
    except Exception as e:
        return None, str(e)

# ------------------------------------------------------------------
root = tk.Tk()
root.title("Find in Current File – Custom Commands Viewer")
root.geometry("1000x740")
root.minsize(750, 500)

settings_path = get_vscode_settings_path()
if not settings_path:
    Label(root, text="Could not find VS Code settings.json", fg="red", font=("", 12)).pack(pady=60)
    Button(root, text="Close", command=root.destroy).pack()
    root.mainloop()
    raise SystemExit

Label(root, text="Find in Current File – Custom Commands", font=("Segoe UI", 16, "bold")).pack(pady=15)
Label(root, text=f"Found settings at:\n{settings_path}", fg="darkgreen", font=("Consolas", 9)).pack(pady=(0,15))

data, error = load_settings_jsonc(settings_path)
if error:
    Label(root, text=f"Error reading file:\n{error}", fg="red").pack(pady=20)
    Button(root, text="Close", command=root.destroy).pack()
    root.mainloop()
    raise SystemExit

ext_settings = data.get(EXTENSION_ID, {})

# This message now uses the actual variable!
if not ext_settings:
    Label(
        root,
        text=f"No custom commands found under the key:\n\"{EXTENSION_ID}\"",
        fg="orange",
        font=("Consolas", 11)
    ).pack(pady=50)
else:
    frame = Frame(root)
    frame.pack(fill="both", expand=True, padx=20, pady=10)

    scrollbar = Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")
    lb = Listbox(frame, font=("Consolas", 10), yscrollcommand=scrollbar.set)
    lb.pack(fill="both", expand=True)
    scrollbar.config(command=lb.yview)

    for cmd_name, cfg in ext_settings.items():
        title = cfg.get("title", "(no title)")
        desc = cfg.get("description", "(no description)").splitlines()[0]
        find_count = len(cfg.get("find", []))
        replace_count = len(cfg.get("replace", []))
        regex = "Yes" if cfg.get("isRegex") is True else "No"

        lb.insert(END, f"Command → {cmd_name}")
        lb.insert(END, f"   Title       : {title}")
        lb.insert(END, f"   Description : {desc}")
        lb.insert(END, f"   Patterns    : {find_count} find → {replace_count} replace")
        lb.insert(END, f"   Regex       : {regex}")
        lb.insert(END, "-" * 90)

    Label(root, text=f"Found {len(ext_settings)} custom command(s)", fg="gray11").pack(pady=12)

Button(root, text="Close", command=root.destroy).pack(pady=15)
root.mainloop()