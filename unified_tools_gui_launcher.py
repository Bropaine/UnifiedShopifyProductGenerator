"""
Unified Tools GUI Launcher
--------------------------
Central GUI hub to launch all your menu/category/product tools:
- Menu Editor (nav + aliases)
- Filename Validator
- Category Path Extractor
- Product Data Generator (future)

Add new tools here as your workflow grows.
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import os

# Map tool names to script paths (customize these as needed)
TOOLS = {
    "Menu Editor": "menu_editor.py",
    "Filename Validator": "validate_filenames.py",
    "Extract Category Paths": "product_category_paths_extractor.py",
    "Product Data Generator": "main.py",
    "Product Data Upload to Host Server": "upload_products_js.py",
    "Backfill Variant Ids": "backfill_variant_ids.py",
}

def launch_script(script_name):
    """Launch a script in a new process."""
    py_exec = sys.executable
    script_path = os.path.abspath(script_name)
    if not os.path.exists(script_path):
        messagebox.showerror("Error", f"Script not found: {script_path}")
        return
    subprocess.Popen([py_exec, script_path])

def main():
    root = tk.Tk()
    root.title("Unified Tools Toolbox")

    tk.Label(root, text="Select a Tool:").pack(pady=10)
    for tool, script in TOOLS.items():
        tk.Button(root, text=tool, width=30, command=lambda s=script: launch_script(s)).pack(pady=4)

    root.mainloop()

if __name__ == "__main__":
    main()
