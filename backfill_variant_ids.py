import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import json
import requests
import threading
import subprocess
from dotenv import load_dotenv

# --- ENV VARS ---
load_dotenv()
DEFAULT_SHOP = os.getenv("SHOPIFY_SHOP", "")
DEFAULT_TOKEN = os.getenv("SHOPIFY_TOKEN", "")


# --- Business Logic (unchanged except param passing) ---

def load_products_js(filename):
    with open(filename, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        start = raw.find('[')
        end = raw.rfind(']')
        if start == -1 or end == -1 or start > end:
            raise Exception("Could not find JSON array in file.")
        json_str = raw[start:end + 1]
        return json.loads(json_str)


def write_products_js(products, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("window.products = ")
        json.dump(products, f, ensure_ascii=False, indent=2)
        f.write(";\n")


def get_all_shopify_products(shop, token, log=lambda msg, color=None: None):
    products = []
    url = f"https://{shop}/admin/api/2024-04/products.json"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    params = {"limit": 250}
    page = 1
    while True:
        log(f"Fetching page {page} of Shopify products...", "blue")
        resp = requests.get(url, headers=headers, params=params)
        data = resp.json()
        if "products" not in data:
            log("Error fetching products: " + str(data), "red")
            break
        batch = data["products"]
        products.extend(batch)
        if len(batch) < 250:
            break
        page += 1
    return products


# --- GUI ---

class VariantBackfillGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopify Variant ID Backfiller")
        self.geometry("670x430")
        instructions = (
            "How to use:\n"
            "1. Confirm that 'products.js' (from product generator) exists in this folder.\n"
            "2. Enter your Shopify Shop and Token below (prefilled from .env if present).\n"
            "3. Click 'Run Backfill' after importing your products to Shopify via CSV.\n"
            "4. This will update 'products.js' with the correct Shopify Variant IDs."
        )
        tk.Label(self, text=instructions, justify="left", wraplength=630).pack(pady=7)

        frm = tk.Frame(self)
        frm.pack(pady=8, fill='x')

        tk.Label(frm, text="Shopify Shop (e.g. yourshop.myshopify.com):").grid(row=0, column=0, sticky='w')
        self.shop_entry = tk.Entry(frm, width=54)
        self.shop_entry.grid(row=0, column=1)
        self.shop_entry.insert(0, DEFAULT_SHOP)

        tk.Label(frm, text="Shopify Token:").grid(row=1, column=0, sticky='w')
        self.token_entry = tk.Entry(frm, width=54, show="*")
        self.token_entry.grid(row=1, column=1)
        self.token_entry.insert(0, DEFAULT_TOKEN)

        self.run_btn = tk.Button(self, text="Run Backfill", command=self.run_backfill)
        self.run_btn.pack(pady=18)

        self.log = scrolledtext.ScrolledText(self, height=10, width=82, state="disabled", wrap="word",
                                             font=("Consolas", 10))
        self.log.pack(pady=4, fill="both", expand=True)

        self.link_labels = []

    def log_msg(self, msg, color="black"):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", color)
        self.log.tag_configure("blue", foreground="#176ad4")
        self.log.tag_configure("green", foreground="#298e46")
        self.log.tag_configure("red", foreground="#b03030")
        self.log.tag_configure("black", foreground="#222")
        self.log.see("end")
        self.log.config(state="disabled")

    def show_file_link(self, path, description):
        def callback(event=None):
            abs_path = os.path.abspath(path)
            folder = os.path.dirname(abs_path)
            try:
                if sys.platform.startswith("win"):
                    subprocess.Popen(['explorer', '/select,', abs_path])
                elif sys.platform == "darwin":
                    subprocess.Popen(['open', '-R', abs_path])
                else:
                    subprocess.Popen(['xdg-open', folder])
            except Exception as ex:
                messagebox.showerror("Error", f"Could not open file location:\n{ex}")

        link = tk.Label(self, text=f"Open {description}: {os.path.basename(path)}", fg="#176ad4", cursor="hand2",
                        wraplength=600)
        link.pack()
        link.bind("<Button-1>", callback)
        self.link_labels.append(link)

    def run_backfill(self):
        shop = self.shop_entry.get().strip()
        token = self.token_entry.get().strip()
        if not (shop and token):
            messagebox.showerror("Error", "Please fill both credential fields.")
            return
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.run_btn.config(state="disabled")
        for lbl in self.link_labels:
            lbl.destroy()
        self.link_labels.clear()
        threading.Thread(target=self._backfill, args=(shop, token), daemon=True).start()

    def _backfill(self, shop, token):
        try:
            js_file = "products.js"
            if not os.path.isfile(js_file):
                self.log_msg("Error: 'products.js' not found in this folder.", "red")
                return
            self.log_msg("Loading products.js...", "blue")
            products = load_products_js(js_file)
            self.log_msg(f"  ✓ Loaded {len(products)} products from products.js", "green")
            self.log_msg("Fetching all Shopify products...", "blue")
            shopify_products = get_all_shopify_products(shop, token, self.log_msg)
            self.log_msg(f"  ✓ Fetched {len(shopify_products)} Shopify products.", "green")

            self.log_msg("Matching and backfilling Variant IDs...", "blue")
            shopify_map = {}
            for prod in shopify_products:
                for variant in prod.get("variants", []):
                    shopify_map[(prod["title"].strip(), float(variant["price"]))] = str(variant["id"])

            not_found = []
            updated = 0
            for p in products:
                key = (p["name"].strip(), float(p["price"]))
                variant_id = shopify_map.get(key)
                if variant_id:
                    p["shopifyVariantId"] = variant_id
                    updated += 1
                else:
                    not_found.append(p["id"])

            write_products_js(products, js_file)
            self.log_msg(f"Updated {updated} products with variant IDs.", "green")
            self.show_file_link(js_file, "products.js (frontend)")

            if not_found:
                self.log_msg(f"WARNING: {len(not_found)} products could not be matched and updated.", "red")
                for pid in not_found:
                    self.log_msg(f"  - {pid}", "red")
            else:
                self.log_msg("All products matched successfully!", "green")
            self.log_msg("\nDone. You may now deploy products.js to your static site. By using Product Data Upload to "
                         "Host Server Tool.", "blue")
        except Exception as ex:
            self.log_msg(f"Error: {ex}", "red")
            messagebox.showerror("Failed", str(ex))
        finally:
            self.run_btn.config(state="normal")


if __name__ == "__main__":
    VariantBackfillGUI().mainloop()
