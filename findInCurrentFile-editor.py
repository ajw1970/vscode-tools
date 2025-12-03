# findInCurrentFile-editor.py  ←  INTERACTIVE EDITOR VERSION
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import json5

try:
    import json5
except ImportError:
    messagebox.showerror("Missing json5", "Run once:\n    pip install json5")
    raise

EXTENSION_ID = "findInCurrentFile"

def get_vscode_settings_path() -> Path | None:
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    candidates = [
        Path(appdata) / "Code" / "User" / "settings.json",
        Path(appdata) / "Code - Insiders" / "User" / "settings.json",
        Path(appdata) / "VSCodium" / "User" / "settings.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def load_settings(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json5.load(f)

def save_settings(path: Path, data: dict):
    # Write with proper formatting and preserve comments via json5
    with open(path, "w", encoding="utf-8") as f:
        json5.dump(data, f, indent=4, quote_keys=True, trailing_commas=False)

# ===================================================================
class CommandEditor(tk.Toplevel):
    def __init__(self, parent, cmd_name: str, cfg: dict, callback):
        super().__init__(parent)
        self.cmd_name = cmd_name
        self.cfg = cfg.copy()
        self.callback = callback

        self.title(f"Edit Command: {cmd_name}")
        self.geometry("800x700")
        self.resizable(True, True)
        self.grab_set()

        ttk.Label(self, text=f"Command Key (cannot be changed):", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        ttk.Entry(self, text=cmd_name, state="readonly").pack(fill="x", padx=20, pady=(0,15))

        # Title
        ttk.Label(self, text="Title:").pack(anchor="w", padx=20, pady=(5,2))
        self.title_var = tk.StringVar(value=cfg.get("title", ""))
        ttk.Entry(self, textvariable=self.title_var, width=80).pack(fill="x", padx=20, pady=(0,10))

        # Description
        ttk.Label(self, text="Description:").pack(anchor="w", padx=20, pady=(10,2))
        self.desc_text = scrolledtext.ScrolledText(self, height=4, wrap="word")
        self.desc_text.insert("1.0", cfg.get("description", ""))
        self.desc_text.pack(fill="both", expand=True, padx=20, pady=(0,10))

        # Regex checkbox
        self.regex_var = tk.BooleanVar(value=bool(cfg.get("isRegex")))
        ttk.Checkbutton(self, text="Use Regular Expressions (isRegex)", variable=self.regex_var).pack(anchor="w", padx=20, pady=5)

        # Find patterns
        ttk.Label(self, text="Find Patterns (one per line):").pack(anchor="w", padx=20, pady=(15,2))
        self.find_text = scrolledtext.ScrolledText(self, height=6)
        self.find_text.insert("1.0", "\n".join(cfg.get("find", [])))
        self.find_text.pack(fill="both", expand=True, padx=20, pady=(0,10))

        # Replace patterns
        ttk.Label(self, text="Replace With (one per line, same count as Find):").pack(anchor="w", padx=20, pady=(10,2))
        self.replace_text = scrolledtext.ScrolledText(self, height=6)
        self.replace_text.insert("1.0", "\n".join(cfg.get("replace", [])))
        self.replace_text.pack(fill="both", expand=True, padx=20, pady=(0,15))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

    def save(self):
        find_lines = [line.strip() for line in self.find_text.get("1.0", "end-1c").splitlines() if line.strip()]
        replace_lines = [line.strip() for line in self.replace_text.get("1.0", "end-1c").splitlines() if line.strip()]

        if len(find_lines) != len(replace_lines) and replace_lines:
            messagebox.showerror("Error", "Number of 'find' and 'replace' lines must match (or replace can be empty).")
            return

        self.cfg.update({
            "title": self.title_var.get().strip() or "(no title)",
            "description": self.desc_text.get("1.0", "end-1c").strip(),
            "isRegex": self.regex_var.get(),
            "find": find_lines,
            "replace": replace_lines if replace_lines else []
        })

        self.callback(self.cmd_name, self.cfg)
        self.destroy()

# ===================================================================
class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Find in Current File – Custom Commands Editor")
        self.root.geometry("1100x800")
        self.root.minsize(900, 600)

        self.settings_path = get_vscode_settings_path()
        if not self.settings_path:
            messagebox.showerror("Error", "Could not find VS Code settings.json")
            root.destroy()
            return

        ttk.Label(root, text="Find in Current File – Custom Commands Editor", font=("Segoe UI", 16, "bold")).pack(pady=15)
        ttk.Label(root, text=f"Settings file: {self.settings_path}", foreground="darkgreen", font=("Consolas", 9)).pack(pady=(0,15))

        # Button bar
        top_bar = ttk.Frame(root)
        top_bar.pack(fill="x", padx=20, pady=(0,10))
        ttk.Button(top_bar, text="Add New Command", command=self.add_new_command).pack(side="left")
        ttk.Button(top_bar, text="Refresh", command=self.reload).pack(side="left", padx=(10,0))
        ttk.Button(top_bar, text="Close", command=root.destroy).pack(side="right")

        # Scrollable canvas for command cards
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.canvas = canvas
        self.frames = {}  # cmd_name -> frame

        self.reload()

    def reload(self):
        data = load_settings(self.settings_path)
        self.settings_data = data
        self.ext_settings = data.get(EXTENSION_ID, {})

        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.frames.clear()

        if not self.ext_settings:
            ttk.Label(self.scrollable_frame, text="No custom commands found.\nClick 'Add New Command' to create one.", 
                     foreground="orange", font=("Segoe UI", 11)).pack(pady=50)
            return

        for cmd_name, cfg in self.ext_settings.items():
            self.add_command_card(cmd_name, cfg)

        ttk.Label(self.root, text=f"{len(self.ext_settings)} command(s) loaded", foreground="gray40").pack(pady=10)

    def add_command_card(self, cmd_name: str, cfg: dict):
        frame = ttk.Frame(self.scrollable_frame, relief="groove", padding=15, borderwidth=2)
        frame.pack(fill="x", pady=8, padx=10)

        # Header
        header = ttk.Frame(frame)
        header.pack(fill="x")
        ttk.Label(header, text=cmd_name, font=("Consolas", 12, "bold")).pack(side="left")
        ttk.Button(header, text="Edit", command=lambda: self.edit_command(cmd_name, cfg)).pack(side="right")
        ttk.Button(header, text="Delete", command=lambda: self.delete_command(cmd_name)).pack(side="right", padx=(5,0))

        # Details
        ttk.Label(frame, text=f"Title: {cfg.get('title', '(no title)')}", foreground="navy").pack(anchor="w")
        desc = cfg.get("description", "").strip().splitlines()[0] if cfg.get("description") else "(no description)"
        ttk.Label(frame, text=f"Desc: {desc}").pack(anchor="w")
        ttk.Label(frame, text=f"Patterns: {len(cfg.get('find', []))} find → {len(cfg.get('replace', []))} replace").pack(anchor="w")
        ttk.Label(frame, text=f"Regex: {'Yes' if cfg.get('isRegex') else 'No'}").pack(anchor="w")

        self.frames[cmd_name] = frame

    def edit_command(self, cmd_name: str, cfg: dict):
        CommandEditor(self.root, cmd_name, cfg, self.save_command_callback)

    def save_command_callback(self, cmd_name: str, new_cfg: dict):
        self.settings_data.setdefault(EXTENSION_ID, {})[cmd_name] = new_cfg
        save_settings(self.settings_path, self.settings_data)
        messagebox.showinfo("Saved", f"Command '{cmd_name}' saved successfully!")
        self.reload()

    def delete_command(self, cmd_name: str):
        if messagebox.askyesno("Delete", f"Delete command '{cmd_name}' permanently?"):
            self.settings_data.setdefault(EXTENSION_ID, {}).pop(cmd_name, None)
            save_settings(self.settings_path, self.settings_data)
            self.reload()

    def add_new_command(self):
        new_key = simpledialog.askstring("New Command", "Enter a unique command key (e.g. myFixDates):")
        if not new_key or not new_key.strip():
            return
        new_key = new_key.strip()
        if new_key in self.settings_data.get(EXTENSION_ID, {}):
            messagebox.showerror("Error", "That command key already exists!")
            return

        empty_cfg = {
            "title": "New Command",
            "description": "Describe what this does",
            "isRegex": False,
            "find": ["old text"],
            "replace": ["new text"]
        }
        CommandEditor(self.root, new_key, empty_cfg, self.save_command_callback)

# ===================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()