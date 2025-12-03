# findInCurrentFile-editor.py  ←  NOW WITH AUTOMATIC BACKUPS
import os
import shutil
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import json5

# === BACKUP CONFIGURATION ===
MAX_BACKUPS = 20
BACKUP_DIR_NAME = "settings-backups"
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

def ensure_backup_dir(settings_path: Path):
    backup_dir = settings_path.parent / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    return backup_dir

def create_backup(settings_path: Path):
    if not settings_path.exists():
        return
    backup_dir = ensure_backup_dir(settings_path)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"settings.json.backup-{timestamp}.json"
    shutil.copy2(settings_path, backup_path)  # copy2 preserves metadata

    # Keep only the newest MAX_BACKUPS
    backups = sorted(backup_dir.glob("settings.json.backup-*.json"), 
                     key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[MAX_BACKUPS:]:
        try:
            old.unlink()
        except:
            pass

def save_settings(path: Path, data: dict):
    """Save with automatic backup first"""
    create_backup(path)  # ← This is the only line you needed to add!
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
        self.geometry("900x800")
        self.resizable(True, True)
        self.grab_set()

        # === Header ===
        ttk.Label(self, text=f"Command Key (cannot be changed):", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        ttk.Entry(self, text=cmd_name, state="readonly").pack(fill="x", padx=20, pady=(0,15))

        # Title
        ttk.Label(self, text="Title:").pack(anchor="w", padx=20, pady=(10,2))
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

        # === Paired Find/Replace Table ===
        ttk.Label(self, text="Find → Replace Patterns:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(15,5))

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Treeview with two columns
        columns = ("find", "replace")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        self.tree.heading("find", text="Find Pattern")
        self.tree.heading("replace", text="Replace With")
        self.tree.column("find", width=400, anchor="w")
        self.tree.column("replace", width=400, anchor="w")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Load existing pairs
        self.load_pairs()

        # Buttons below table
        btns = ttk.Frame(self)
        btns.pack(pady=8)
        ttk.Button(btns, text="Add Row", command=self.add_row).pack(side="left", padx=5)
        ttk.Button(btns, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)
        ttk.Button(btns, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        ttk.Button(btns, text="Move Up", command=self.move_up).pack(side="left", padx=5)
        ttk.Button(btns, text="Move Down", command=self.move_down).pack(side="left", padx=5)

        # Save/Cancel
        save_btn_frame = ttk.Frame(self)
        save_btn_frame.pack(pady=20)
        ttk.Button(save_btn_frame, text="Save", command=self.save).pack(side="left", padx=10)
        ttk.Button(save_btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

        # Double-click to edit
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def load_pairs(self):
        finds = self.cfg.get("find", [])
        replaces = self.cfg.get("replace", [])
        max_len = max(len(finds), len(replaces))
        for i in range(max_len):
            f = finds[i] if i < len(finds) else ""
            r = replaces[i] if i < len(replaces) else ""
            self.tree.insert("", "end", values=(f, r))

    def get_pairs(self):
        pairs = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            find_val = values[0].strip()
            replace_val = values[1].strip()
            if find_val:  # only include if find is non-empty
                pairs.append((find_val, replace_val))
        return pairs

    def add_row(self):
        self.edit_row("", "")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a row to edit.")
            return
        item = selected[0]
        values = self.tree.item(item, "values")
        self.edit_row(values[0], values[1], item)

    def edit_row(self, find_text="", replace_text="", item=None):
        dialog = PairEditDialog(self, find_text, replace_text)
        self.wait_window(dialog)
        if dialog.result:
            find_val, replace_val = dialog.result
            if item:
                self.tree.item(item, values=(find_val, replace_val))
            else:
                self.tree.insert("", "end", values=(find_val, replace_val))

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a row to delete.")
            return
        if messagebox.askyesno("Delete", "Delete selected row(s)?"):
            for item in selected:
                self.tree.delete(item)

    def move_up(self):
        selected = self.tree.selection()
        if not selected: return
        for item in selected:
            idx = self.tree.index(item)
            if idx == 0: continue
            prev = self.tree.get_children()[idx - 1]
            self.tree.move(item, "", idx - 1)
            self.tree.move(prev, "", idx)

    def move_down(self):
        selected = self.tree.selection()
        if not selected: return
        items = list(self.tree.get_children())
        for item in reversed(selected):  # reverse to handle multiple
            idx = self.tree.index(item)
            if idx >= len(items) - 1: continue
            next_item = items[idx + 1]
            self.tree.move(item, "", idx + 1)

    def save(self):
        pairs = self.get_pairs()
        if not pairs:
            if not messagebox.askyesno("No patterns", "You have no find/replace pairs. Save anyway?"):
                return

        find_list = [p[0] for p in pairs]
        replace_list = [p[1] for p in pairs]

        self.cfg.update({
            "title": self.title_var.get().strip() or "(no title)",
            "description": self.desc_text.get("1.0", "end-1c").strip(),
            "isRegex": self.regex_var.get(),
            "find": find_list,
            "replace": replace_list
        })

        self.callback(self.cmd_name, self.cfg)
        self.destroy()


# === Simple dialog for editing a single find/replace pair ===
class PairEditDialog(tk.Toplevel):
    def __init__(self, parent, find_text="", replace_text=""):
        super().__init__(parent)
        self.title("Edit Find → Replace")
        self.geometry("700x200")
        self.resizable(True, False)
        self.grab_set()

        ttk.Label(self, text="Find Pattern:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(20,5))
        self.find_var = tk.StringVar(value=find_text)
        ttk.Entry(self, textvariable=self.find_var, width=80).pack(fill="x", padx=20, pady=(0,10))

        ttk.Label(self, text="Replace With:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(5,5))
        self.replace_var = tk.StringVar(value=replace_text)
        ttk.Entry(self, textvariable=self.replace_var, width=80).pack(fill="x", padx=20, pady=(0,20))

        btns = ttk.Frame(self)
        btns.pack()
        ttk.Button(btns, text="OK", command=self.ok).pack(side="left", padx=10)
        ttk.Button(btns, text="Cancel", command=self.cancel).pack(side="left", padx=10)

        self.result = None

    def ok(self):
        self.result = (self.find_var.get(), self.replace_var.get())
        self.destroy()

    def cancel(self):
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
        ttk.Button(top_bar, text="Restore Last Backup", command=self.restore_last_backup).pack(side="left", padx=(10,0))

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

    def restore_last_backup(self):
        backup_dir = self.settings_path.parent / BACKUP_DIR_NAME
        if not backup_dir.exists():
            messagebox.showinfo("No backups", "No backup folder found.")
            return
        backups = sorted(backup_dir.glob("settings.json.backup-*.json"), 
                        key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            messagebox.showinfo("No backups", "No backup files found.")
            return
        if messagebox.askyesno("Restore", f"Restore from:\n{backups[0].name} ?"):
            shutil.copy2(backups[0], self.settings_path)
            messagebox.showinfo("Restored", "Settings restored! Restarting view...")
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