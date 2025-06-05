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
