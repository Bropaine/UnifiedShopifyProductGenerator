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
    "Extract Category Paths": "product_category_path_extractor.py",
    "Product Data Generator": "main.py",
    "Product Data Upload to Host Server": "upload_products_js.py",
    "Backfill Variant Ids": "backfill_variant_ids.py",
    "Filename Path Builder": "filename_path_builder.py"
}

SPLASH_TEXT = """
🛠️ Unified Shopify & Static Site Product Toolkit — Workflow Overview

Welcome! This toolkit streamlines your human-in-the-loop product workflow for Shopify and your static site.

Typical Usage Sequence: 1.Create Image Filenames with the Filename path builder. Copy and rename images. This picker 
will stay in sync with the valid category paths file.

2. Validate Image Filenames
   - Drop your new product images here to check filename format, category, and subcategory correctness.
   - Only images with valid names/categories should proceed.
   - Format should be category_subcategory1_subcategory2_name-of-product_PRICE-DOUBLE_optional-extra-notes
   - Extra notes can be added for the AI generator for product descriptions, PRICE must be a valid double such as 25.00
   - Supports up to 4 subcategories of depth

2. Extract Category Paths from nav.html
   - Run after editing your website menu. This creates the canonical category path list for all tools.

3. Edit Menu & Aliases
   - Edit your navigation hierarchy, add aliases, and export both nav.html and the category paths file.

4. Generate Shopify CSV & products.js
   - Uses image filenames to create a Shopify CSV and products.js. AI writes product descriptions!

5. Backfill Shopify Variant IDs
   - After you upload the CSV to Shopify, use this to update Shopify variant IDs in products.js.

6. Upload products.js to Website
   - Securely upload the updated products.js to your website for instant product updates.

Human operator is always in control—review every file and step before upload!
"""


def show_splash(parent=None):
    splash = tk.Toplevel(parent)
    splash.title("About — Unified Shopify/Product Toolkit")
    splash.geometry("560x480")
    splash.resizable(False, False)
    splash.attributes('-topmost', True)
    splash.grab_set()
    # Make the splash modal

    text = tk.Text(splash, wrap="word", font=("Segoe UI", 11), padx=16, pady=12, borderwidth=0)
    text.insert("1.0", SPLASH_TEXT)
    text.config(state="disabled", bg="#fafafc")
    text.pack(fill="both", expand=True)
    btn = tk.Button(splash, text="OK", command=splash.destroy, font=("Segoe UI", 10, "bold"), padx=10, pady=5)
    btn.pack(pady=12)
    splash.focus_set()
    splash.transient(parent)
    parent.wait_window(splash)


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

    # Hide window, schedule splash, then show main
    def show_and_hide():
        show_splash(root)
        root.deiconify()

    root.after(0, show_and_hide)  # Show splash after event loop starts

    tk.Label(root, text="Select a Tool:").pack(pady=10)
    for tool, script in TOOLS.items():
        tk.Button(root, text=tool, width=30, command=lambda s=script: launch_script(s)).pack(pady=4)

    root.mainloop()


if __name__ == "__main__":
    main()
