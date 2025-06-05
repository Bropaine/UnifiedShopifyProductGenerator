"""
Category Path Extractor for Static Site Navigation
--------------------------------------------------

This utility parses your site's nav.html and extracts the category path tuples required by menu_editor.py and the product filename validator.

**Where does it fit in the workflow?**
- The static site's nav.html defines your category hierarchy for browsing and product organization.
- This script reads nav.html and generates `Valid_Category_Paths/valid_category_paths.py`, which contains the canonical `VALID_CATEGORY_PATHS` list.
- The `VALID_CATEGORY_PATHS` module is **imported by menu_editor.py** (your visual nav/alias editor) and by your filename validator to ensure category accuracy and alignment with the website menu.

**Typical usage:**
1. You update your site's nav.html menu structure manually or with the GUI menu editor.
2. Run this script to update the canonical category path list in `Valid_Category_Paths/valid_category_paths.py`.
3. Now, both the GUI menu editor and validation tools operate on the real menu structure, ensuring perfect alignment and eliminating mismatches.

**Key points:**
- Dedupe is done *in nav order* so your validator and editor always work in site order, not alphabetical.
- No site code is changed: this only updates the Python file with canonical category paths.
- Changes here are immediately reflected in all tooling and validation scripts, creating a human-in-the-loop, source-of-truth workflow.

See also: menu_editor.py, validate_filenames.py, and your main product pipeline.



Category Path Extractor for Static Site Navigation (GUI)
--------------------------------------------------------
Select your nav.html, extract category paths, and update the canonical Python list used by your site tools.

- Click "Browse" to select nav.html.
- Click "Extract" to generate Valid_Category_Paths/valid_category_paths.py.
- Status messages and output appear below.

See also: menu_editor.py, validate_filenames.py
"""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from bs4 import BeautifulSoup
import os


def extract_paths_from_nav(nav_file):
    with open(nav_file, encoding='utf-8') as f:
        soup = BeautifulSoup(f, "html.parser")

    paths = []

    def walk_menu(ul, path):
        for li in ul.find_all("li", recursive=False):
            a = li.find("a", href=True)
            if a and "category.html" in a["href"]:
                import re
                category_match = re.findall(r'[?&](category|subcategory\d*)=([\w\-]+)', a["href"])
                if category_match:
                    cat_path = [val for key, val in sorted(category_match, key=lambda x: x[0])]
                    paths.append(tuple(cat_path))
            submenu = li.find("ul", class_="submenu")
            if submenu:
                walk_menu(submenu, path)

    nav = soup.find("nav")
    if nav:
        top_ul = nav.find("ul", class_="nav-content")
        if top_ul:
            walk_menu(top_ul, [])

    return paths


class CategoryPathExtractorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Category Path Extractor (nav.html → valid_category_paths.py)")
        self.geometry("600x390")
        self.nav_file = tk.StringVar()

        tk.Label(self, text="Step 1: Browse for your site's nav.html file").pack(pady=6)
        frm = tk.Frame(self)
        frm.pack()
        tk.Entry(frm, textvariable=self.nav_file, width=60, state="readonly").pack(side="left", padx=2)
        tk.Button(frm, text="Browse", command=self.browse_nav).pack(side="left")

        tk.Label(self, text="Step 2: Click 'Extract' to parse and update category path list").pack(pady=10)
        tk.Button(self, text="Extract Category Paths", command=self.extract_and_write).pack()

        self.status = scrolledtext.ScrolledText(self, height=10, wrap="word", state="disabled", font=("Consolas", 10))
        self.status.pack(fill="both", expand=True, pady=8, padx=8)

    def browse_nav(self):
        filename = filedialog.askopenfilename(
            title="Select nav.html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
        )
        if filename:
            self.nav_file.set(filename)

    def extract_and_write(self):
        nav_path = self.nav_file.get()
        if not nav_path or not os.path.isfile(nav_path):
            messagebox.showerror("No file", "Please select a valid nav.html file.")
            return

        out_dir = "Valid_Category_Paths"
        out_file = os.path.join(out_dir, "valid_category_paths.py")

        all_paths = extract_paths_from_nav(nav_path)
        # Deduplicate but preserve nav order!
        seen = set()
        ordered_paths = []
        for p in all_paths:
            if p not in seen:
                seen.add(p)
                ordered_paths.append(p)

        os.makedirs(out_dir, exist_ok=True)

        with open(out_file, "w", encoding="utf-8") as f:
            f.write("VALID_CATEGORY_PATHS = [\n")
            for path in ordered_paths:
                f.write(f"    {path},\n")
            f.write("]\n")

        msg = (
            f"Wrote {len(ordered_paths)} unique category paths to {out_file}\n"
            f"Source nav.html: {nav_path}\n"
            "You can now use menu_editor.py and filename validator with updated category paths."
        )
        self.status.config(state="normal")
        self.status.insert("end", msg + "\n\n")
        self.status.see("end")
        self.status.config(state="disabled")
        messagebox.showinfo("Done", f"Category paths extracted and written to:\n{out_file}")


if __name__ == "__main__":
    CategoryPathExtractorApp().mainloop()
