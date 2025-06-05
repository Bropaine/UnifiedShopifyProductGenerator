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

"""

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

if __name__ == "__main__":
    nav_html_file = "nav/nav.html"  # Change this if your path differs
    out_dir = "Valid_Category_Paths"
    out_file = os.path.join(out_dir, "valid_category_paths.py")

    all_paths = extract_paths_from_nav(nav_html_file)
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

    print(f"Wrote {len(ordered_paths)} unique category paths to {out_file}")
