"""
Unified Shopify Product & Frontend Data Generator - GUI Edition
---------------------------------------------------------------
This GUI automates product data generation for Shopify and a custom static site using
human-curated image filenames (uploaded to Shopify Files) as the *source of truth*.

**How to use:**
1. Upload your product images to Shopify Files (Admin → Content → Files).
   - Filenames must use the correct convention!
2. Fill in your Shopify credentials below (these will be prefilled from .env if present).
3. Click "Run" to fetch all product images, generate descriptions, and export
   BOTH a Shopify product CSV and a JavaScript products.js file for your site.
4. Upload the CSV manually to Shopify (Admin → Products → Import).
5. The products.js file can be used by your static site frontend.

"""

import tkinter as tk
from tkinter import ttk, messagebox
import os
from dotenv import load_dotenv
import threading

# ---- Import your data generation logic ----
import hashlib
import csv
import json
import requests
import openai

load_dotenv()
DEFAULT_SHOP = os.getenv("SHOPIFY_SHOP") or ""
DEFAULT_TOKEN = os.getenv("SHOPIFY_TOKEN") or ""
DEFAULT_OPENAI = os.getenv("OPENAI_API_KEY") or ""

CSV_FIELDNAMES = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Tags", "Published",
    "Option1 Name", "Option1 Value", "Variant Inventory Qty", "Variant Price", "Image Src"
]

def get_shopify_images(shop, token):
    url = f"https://{shop}/admin/api/2025-04/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    has_next_page = True
    after = None
    images = []
    query = """
    query getFiles($cursor: String) {
      files(first: 100, after: $cursor) {
        edges {
          node {
            ... on MediaImage {
              id
              image {
                url
                altText
              }
              originalSource { url }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    while has_next_page:
        variables = {"cursor": after} if after else {}
        response = requests.post(
            url, headers=headers, json={"query": query, "variables": variables}
        )
        result = response.json()
        if "errors" in result:
            raise Exception("Shopify GraphQL query failed: %s" % result["errors"])
        files = result["data"]["files"]["edges"]
        for f in files:
            node = f["node"]
            images.append({
                "url": node["image"]["url"],
                "altText": node["image"].get("altText"),
                "originalSource": node.get("originalSource", {}).get("url")
            })
        has_next_page = result["data"]["files"]["pageInfo"]["hasNextPage"]
        after = result["data"]["files"]["pageInfo"]["endCursor"]
    return images

def parse_image_filename(filename):
    name = os.path.splitext(os.path.basename(filename))[0]
    parts = name.split('_')
    if len(parts) < 4:
        raise ValueError(f"Filename too short: {filename}")
    price = None
    price_idx = None
    for i in range(len(parts) - 1, 0, -1):
        try:
            price = float(parts[i])
            price_idx = i
            break
        except ValueError:
            continue
    if price is None or price_idx is None:
        raise ValueError(f"No valid price found in {filename}")
    extra_notes = ""
    if price_idx < len(parts) - 1:
        extra_notes = "_".join(parts[price_idx + 1:]).replace('-', ' ')
    title_raw = parts[price_idx - 1]
    title = title_raw.replace('-', ' ').title()
    categories = parts[:price_idx - 1]
    base_handle = "-".join(parts[:price_idx]).lower()
    salt = hashlib.sha1(filename.encode()).hexdigest()[:6]
    handle = f"{base_handle}-{salt}"
    tag_labels = ["category", "subcategory1", "subcategory2", "subcategory3", "subcategory4"]
    tags = []
    for i, cat in enumerate(categories):
        if i < len(tag_labels):
            tags.append(f"{tag_labels[i]}:{cat}")
    return {
        "handle": handle,
        "title": title,
        "price": price,
        "categories": categories,
        "tags": tags,
        "extra_notes": extra_notes
    }

def get_ai_description(openai_key, title, tags, extra_notes=""):
    client = openai.OpenAI(api_key=openai_key)
    prompt = (
        "You are a clever, creative copywriter for a cool retro games and collectibles shop. "
        "Write a unique, punchy product description for a web store listing. "
        "Each description should be original (never copy-pasted), natural, and fit the brand’s fun, nostalgic voice.\n"
        f"Product title: {title}\n"
        f"Tags: {', '.join(tags)}\n"
        "Guidelines:\n"
        "- Limit to 30–40 words—concise and scannable.\n"
        "- Do NOT repeat the title or tags verbatim.\n"
        "- Do NOT use generic phrases like 'must-have', 'timeless', 'classic', 'iconic'—be specific and vivid.\n"
        "- If the product is vintage, limited, or rare, highlight this.\n"
        "- Use active, descriptive language that tells the shopper what makes this item special or fun.\n"
        "- If you see details about condition, era, or features (from title or tags), mention them naturally.\n"
    )
    if extra_notes:
        prompt += f"\nExtra notes for the copywriter: {extra_notes}\n"
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def group_images_by_handle(images, openai_key):
    products = []
    for img in images:
        filename = img["url"].split("/")[-1]
        try:
            parsed = parse_image_filename(filename)
        except Exception as ex:
            print(f"Error parsing {filename}: {ex}")
            continue
        handle = parsed["handle"]
        title = parsed["title"]
        price = parsed["price"]
        tags = parsed["tags"]
        extra_notes = parsed.get("extra_notes", "")
        desc = get_ai_description(openai_key, title, tags, extra_notes)
        product = {
            "id": handle,
            "name": title,
            "description": desc,
            "details": desc,
            "price": price,
            "category": parsed["categories"][0] if len(parsed["categories"]) > 0 else "",
            "subcategory1": parsed["categories"][1] if len(parsed["categories"]) > 1 else "",
            "subcategory2": parsed["categories"][2] if len(parsed["categories"]) > 2 else "",
            "subcategory3": parsed["categories"][3] if len(parsed["categories"]) > 3 else "",
            "subcategory4": parsed["categories"][4] if len(parsed["categories"]) > 4 else "",
            "images": [img["url"]],
            "shopifyEmbed": "",
            "shopifyVariantId": "",
            "status": "available",
            "quantity": 1,
            "featured": False
        }
        csv_row = {
            "Handle": handle,
            "Title": title,
            "Body (HTML)": desc,
            "Vendor": "Rewind the Finds",
            "Tags": ", ".join(tags),
            "Published": "TRUE",
            "Option1 Name": "Title",
            "Option1 Value": "Default Title",
            "Variant Inventory Qty": 1,
            "Variant Price": price,
            "Image Src": img["url"],
        }
        products.append({"csv_row": csv_row, "js_product": product})
    return products

def write_csv(products, outfile):
    with open(outfile, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for prod in products:
            writer.writerow(prod["csv_row"])

def write_products_js(products, outfile):
    product_list = [prod["js_product"] for prod in products]
    with open(outfile, "w", encoding="utf-8") as f:
        f.write("window.products = ")
        json.dump(product_list, f, ensure_ascii=False, indent=2)
        f.write(";\n")

# ----------- GUI PART -----------

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import os
import sys
import threading
import subprocess

# ... [rest of your import and business logic code above] ...

class ProductGenGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopify/Static Site Product Data Generator")
        self.geometry("640x420")
        instructions = (
            "How to use:\n"
            "1. Upload product images to Shopify Admin → Content → Files. Filenames MUST follow your naming rules.\n"
            "2. Enter your Shopify Shop, Token, and OpenAI API Key below. These are prefilled from .env if present.\n"
            "3. Click 'Run' to fetch images, generate data, and export shopify_upload.csv & products.js."
        )
        tk.Label(self, text=instructions, justify="left", wraplength=600).pack(pady=6)

        frm = tk.Frame(self)
        frm.pack(pady=10, fill='x')

        tk.Label(frm, text="Shopify Shop (e.g. yourshop.myshopify.com):").grid(row=0, column=0, sticky='w')
        self.shop_entry = tk.Entry(frm, width=48)
        self.shop_entry.grid(row=0, column=1)
        self.shop_entry.insert(0, DEFAULT_SHOP)

        tk.Label(frm, text="Shopify Token:").grid(row=1, column=0, sticky='w')
        self.token_entry = tk.Entry(frm, width=48, show="*")
        self.token_entry.grid(row=1, column=1)
        self.token_entry.insert(0, DEFAULT_TOKEN)

        tk.Label(frm, text="OpenAI API Key:").grid(row=2, column=0, sticky='w')
        self.openai_entry = tk.Entry(frm, width=48, show="*")
        self.openai_entry.grid(row=2, column=1)
        self.openai_entry.insert(0, DEFAULT_OPENAI)

        self.run_btn = tk.Button(self, text="Run", command=self.run_generator)
        self.run_btn.pack(pady=18)

        # Use a scrolled text for multi-line status updates
        self.log = scrolledtext.ScrolledText(self, height=10, width=80, state="disabled", wrap="word", font=("Consolas", 10))
        self.log.pack(pady=4, fill="both", expand=True)

        # Placeholders for hyperlink labels
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

    def run_generator(self):
        shop = self.shop_entry.get().strip()
        token = self.token_entry.get().strip()
        openai_key = self.openai_entry.get().strip()
        if not (shop and token and openai_key):
            messagebox.showerror("Error", "Please fill all credential fields.")
            return
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.log_msg("Starting product data generation...\n", "blue")
        self.run_btn.config(state="disabled")
        for lbl in self.link_labels:
            lbl.destroy()
        self.link_labels.clear()
        threading.Thread(target=self._generate, args=(shop, token, openai_key), daemon=True).start()

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

        link = tk.Label(self, text=f"Open {description}: {os.path.basename(path)}", fg="#176ad4", cursor="hand2", wraplength=570)
        link.pack()
        link.bind("<Button-1>", callback)
        self.link_labels.append(link)

    def _generate(self, shop, token, openai_key):
        try:
            self.log_msg("Fetching images from Shopify...", "blue")
            images = get_shopify_images(shop, token)
            self.log_msg(f"  ✓ {len(images)} images found.", "green")
            self.log_msg("Parsing image filenames...", "blue")
            # (Could add per-file logs here if desired)
            self.log_msg("Generating product descriptions with OpenAI...", "blue")
            products = group_images_by_handle(images, openai_key)
            self.log_msg(f"  ✓ {len(products)} products generated.", "green")
            out_csv = "shopify_upload.csv"
            out_js = "products.js"
            self.log_msg("Writing Shopify CSV...", "blue")
            write_csv(products, out_csv)
            self.log_msg("  ✓ shopify_upload.csv written.", "green")
            self.log_msg("Writing products.js...", "blue")
            write_products_js(products, out_js)
            self.log_msg("  ✓ products.js written.", "green")
            self.log_msg("\nAll done! See files below.", "green")
            self.show_file_link(out_csv, "Shopify CSV")
            self.show_file_link(out_js, "products.js (frontend)")
            self.log_msg("Run Backfill Variant Ids on products.js After Uploading CSV to Shopify", "blue")
            self.log_msg("Review and import CSV in Shopify Admin > Products > Import.", "blue")
        except Exception as ex:
            self.log_msg(f"Error: {ex}", "red")
            messagebox.showerror("Failed", str(ex))
        finally:
            self.run_btn.config(state="normal")

# --- rest of your business logic as before ---

if __name__ == "__main__":
    ProductGenGUI().mainloop()
