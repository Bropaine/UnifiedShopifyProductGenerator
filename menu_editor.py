"""
Menu Hierarchy GUI Editor for Static Site Navigation
----------------------------------------------------

**Purpose:**
A visual tool for managing your site's category/menu structure and display aliases, with direct export of both:
- `nav/nav.html` (used by your static site as the main navigation menu)
- `Valid_Category_Paths/valid_category_paths.py` (used by your filename validator, pipeline, and other tools)

**How it fits in your workflow:**
1. Edit categories/aliases/structure visually (add, remove, alias, or reorder).
2. Export updates both your actual nav menu (HTML) and the canonical category path list (Python).
3. All product validation and data generation tools downstream reference the same canonical category structure—no mismatches, no manual syncing.
4. *Supports “blank” keys for catch-all nodes, aligning with how your menu and validator expect category URLs.*

**Key Features:**
- Tree-based editor allows hierarchical editing of both keys (URL-safe, internal) and display aliases.
- Optionally supports “blank” keys for all-encompassing menu items.
- Prevents duplicate keys at the same menu level, enforcing consistency.
- Direct export of HTML and Python for seamless static site and tooling integration.
- “Human-in-the-loop” design keeps you in control, but ensures everything stays in sync.

**Related scripts/tools:**
- `extract_category_paths.py`: parses your nav HTML and generates valid_category_paths.py
- `validate_filenames.py`: validates product images/filenames against canonical paths
- Your product data generator scripts (Shopify/JS/CSV, etc.)

**Typical workflow:**
- Update categories/aliases in this editor → Export → (optionally) run validator or data generator → Deploy!

"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import os
import importlib.util

PATHS_FILE = os.path.join("Valid_Category_Paths", "valid_category_paths.py")

def load_category_paths(path_file):
    spec = importlib.util.spec_from_file_location("valid_category_paths", path_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.VALID_CATEGORY_PATHS)

def build_tree(paths, aliases=None):
    tree = {}
    aliases = aliases or {}
    for p in paths:
        node = tree
        for level in p:
            key = level
            alias = aliases.get(level, key.replace('-', ' ').title()) if key else aliases.get("", "(blank)")
            if key not in node:
                node[key] = {"key": key, "alias": alias, "children": {}}
            node = node[key]["children"]
    return tree

def flatten_tree(tree, prefix=None):
    """Returns a list of all canonical key paths from root to leaf."""
    paths = []
    prefix = prefix or []
    for node in tree.values():
        key = node["key"]
        if node["children"]:
            paths.extend(flatten_tree(node["children"], prefix + [key]))
        else:
            paths.append(tuple(prefix + [key]))
    return paths

def build_nav_html(tree, indent=2, parent_keys=()):
    """Recursive function to build nested <ul>/<li> menu from tree (uses alias as display name)."""
    html = []
    pad = ' ' * indent
    if indent == 2:
        ul_attrs = ' class="nav-content" id="mobile-nav"'
    else:
        ul_attrs = ' class="submenu"'
    html.append(f'{pad}<ul{ul_attrs}>')
    for node in tree.values():
        key = node["key"]
        alias = node["alias"]
        subtree = node["children"]
        if subtree:
            html.append(f'{pad}  <li>')
            html.append(f'{pad}    <button class="submenu-toggle" aria-expanded="false">{alias}</button>')
            html.extend(build_nav_html(subtree, indent + 4, parent_keys + (key,)))
            html.append(f'{pad}  </li>')
        else:
            # Build category URL parts, skip blank keys
            all_keys = list(parent_keys) + [key]
            url_parts = []
            if all_keys and all_keys[0]:
                url_parts.append(f'category={all_keys[0]}')
            sub_idx = 1
            for val in all_keys[1:]:
                if val != "":
                    url_parts.append(f'subcategory{sub_idx}={val}')
                    sub_idx += 1
            url = "category.html"
            if url_parts:
                url += "?" + "&".join(url_parts)
            html.append(f'{pad}  <li><a href="{url}" class="nav-link">{alias}</a></li>')
    html.append(f'{pad}</ul>')
    return html

class NodeDialog(simpledialog.Dialog):
    def __init__(self, parent, title, key="", alias="", is_new=True, sibling_keys=None):
        self.key = key
        self.alias = alias
        self.is_new = is_new
        self.sibling_keys = sibling_keys or []
        super().__init__(parent, title)

    def body(self, frame):
        tk.Label(frame, text="Key (internal, URL-safe, unique; leave blank for 'all' node):").grid(row=0, column=0, sticky='e')
        self.key_var = tk.StringVar(value=self.key)
        self.key_entry = tk.Entry(frame, textvariable=self.key_var)
        self.key_entry.grid(row=0, column=1)
        if not self.is_new:
            self.key_entry.config(state="disabled")  # Key can't be edited when renaming/alias only

        tk.Label(frame, text="Alias (display name):").grid(row=1, column=0, sticky='e')
        self.alias_var = tk.StringVar(value=self.alias)
        self.alias_entry = tk.Entry(frame, textvariable=self.alias_var)
        self.alias_entry.grid(row=1, column=1)
        return self.key_entry

    def validate(self):
        key = self.key_var.get().strip()
        # Allow blank key
        if key and (' ' in key or not all(c.isalnum() or c in "-_" for c in key)):
            messagebox.showerror("Validation", "Key must be URL-safe (letters, numbers, -, _ only, no spaces).")
            return False
        if self.is_new and key in self.sibling_keys:
            messagebox.showerror("Validation", f"Key '{key}' already exists at this level.")
            return False
        alias = self.alias_var.get().strip()
        if not alias:
            messagebox.showerror("Validation", "Alias (display name) is required.")
            return False
        return True

    def apply(self):
        self.result = (self.key_var.get().strip(), self.alias_var.get().strip())

class MenuEditorApp:
    def __init__(self, master, tree):
        self.master = master
        self.tree_data = tree
        self.tk_tree = ttk.Treeview(master)
        self.tk_tree.pack(fill='both', expand=True)

        btns = tk.Frame(master)
        btns.pack()

        tk.Button(btns, text="Add Parent", command=self.add_parent).pack(side='left')
        tk.Button(btns, text="Add Child", command=self.add_child).pack(side='left')
        tk.Button(btns, text="Edit Alias", command=self.edit_alias).pack(side='left')
        tk.Button(btns, text="Remove Selected", command=self.remove_selected).pack(side='left')
        tk.Button(btns, text="Export", command=self.export_all).pack(side='left')

        self.populate_tree("", self.tree_data)

    def populate_tree(self, parent, subtree):
        for node in subtree.values():
            display_key = node['key'] if node['key'] else "(blank)"
            node_id = self.tk_tree.insert(parent, "end", text=f"{display_key} | {node['alias']}")
            if node["children"]:
                self.populate_tree(node_id, node["children"])

    def get_tree_path(self, item):
        path = []
        while item:
            label = self.tk_tree.item(item, "text")
            key = label.split(" | ")[0]
            if key == "(blank)":
                key = ""
            path.insert(0, key)
            item = self.tk_tree.parent(item)
        return path

    def add_parent(self):
        dialog = NodeDialog(self.master, "Add Parent", key="", alias="", is_new=True, sibling_keys=self.tree_data.keys())
        if dialog.result:
            key, alias = dialog.result
            self.tree_data[key] = {"key": key, "alias": alias, "children": {}}
            self.tk_tree.insert("", "end", text=f"{key if key else '(blank)'} | {alias}")

    def add_child(self):
        selected = self.tk_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a parent node.")
            return
        parent_item = selected[0]
        parent_path = self.get_tree_path(parent_item)
        parent_node = self.tree_data
        for level in parent_path:
            parent_node = parent_node[level]["children"]
        dialog = NodeDialog(self.master, "Add Child", key="", alias="", is_new=True, sibling_keys=parent_node.keys())
        if dialog.result:
            key, alias = dialog.result
            parent_node[key] = {"key": key, "alias": alias, "children": {}}
            self.tk_tree.insert(parent_item, "end", text=f"{key if key else '(blank)'} | {alias}")

    def edit_alias(self):
        selected = self.tk_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a node to edit.")
            return
        item = selected[0]
        path = self.get_tree_path(item)
        node = self.tree_data
        for level in path:
            node = node[level]
        dialog = NodeDialog(self.master, "Edit Alias", key=node["key"], alias=node["alias"], is_new=False)
        if dialog.result:
            _, new_alias = dialog.result
            node["alias"] = new_alias
            display_key = node['key'] if node['key'] else "(blank)"
            self.tk_tree.item(item, text=f"{display_key} | {new_alias}")

    def remove_selected(self):
        selected = self.tk_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a node to remove.")
            return
        item = selected[0]
        path = self.get_tree_path(item)
        if messagebox.askokcancel("Confirm", f"Remove category path: {' → '.join(path)} ?"):
            parent_node = self.tree_data
            for level in path[:-1]:
                parent_node = parent_node[level]["children"]
            del parent_node[path[-1]]
            self.tk_tree.delete(item)

    def export_all(self):
        # 1. Export valid_category_paths.py (canonical keys)
        paths = flatten_tree(self.tree_data)
        out_dir = "Valid_Category_Paths"
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "valid_category_paths.py")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("VALID_CATEGORY_PATHS = [\n")
            for p in paths:
                f.write(f"    {p},\n")
            f.write("]\n")

        # 2. Export nav.html (using aliases for menu display)
        html_lines = [
            "<!-- NAV Starts Here!!! -->",
            "<nav>",
            '  <button class="hamburger" aria-label="Menu" aria-controls="mobile-nav" aria-expanded="false">',
            "    <span></span><span></span><span></span>",
            "  </button>"
        ]
        html_lines += build_nav_html(self.tree_data, indent=2)
        html_lines += [
            '  <div class="nav-bar-spacer"></div>',
            '    <a href="cart.html" class="cart-link" aria-label="View cart">',
            '      <span class="cart-icon">&#128722;</span>',
            '      <span class="cart-count" id="cart-count">0</span>',
            '    </a>',
            '</nav>',
            "<!-- NAV Ends Here!!! -->"
        ]
        nav_out_file = os.path.join("nav", "nav.html")
        os.makedirs("nav", exist_ok=True)
        with open(nav_out_file, "w", encoding="utf-8") as f:
            f.write('\n'.join(html_lines))

        messagebox.showinfo("Exported",
                            f"Exported {len(paths)} paths to {out_file}\nExported nav HTML to {nav_out_file}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Menu Hierarchy Editor (with Aliases & Optional Keys)")
    paths = load_category_paths(PATHS_FILE)
    tree = build_tree(paths)
    app = MenuEditorApp(root, tree)
    root.mainloop()
