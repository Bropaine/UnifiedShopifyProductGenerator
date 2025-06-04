"""
Unified Shopify Product & Frontend Data Generator
-------------------------------------------------
This script is the first step in a human-in-the-loop, two-stage product workflow.

**Purpose:** - To automate product data generation for Shopify and a custom static site using human-curated image
filenames as the *source of truth*. - For each product image file (named with a specific, human-managed convention),
this script: - Parses the filename for category, title, and price. - Generates unique, salted product handles to
ensure Shopify compatibility. - Uses OpenAI to generate human-quality product descriptions. - Outputs: - A Shopify
product CSV for *manual review and upload* by the operator (the human). - A JavaScript/JSON product data file for the
static frontend.

**Workflow:** 1. The human operator uploads new product images (with strict naming) to Shopify. 2. This script is run
to generate both the CSV and the `products.js` file. 3. The human reviews and uploads the CSV via Shopify Admin (
triggering product creation). 4. Once Shopify has created the products, the operator runs `backfill_variant_ids.py`
to fetch and populate the Shopify variant IDs in the static site data.

**Key Principle:**
- Humans make the key decisions about product content, inventory, and timing.
- The pipeline automates tedious data prep, but keeps the operator in control and in the loop.

See `backfill_variant_ids.py` for stage two of the workflow.
"""

import csv
import hashlib
import json
import os
import openai
import requests
from dotenv import load_dotenv

# --- Load env vars ---
load_dotenv()
SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP")
SHOPIFY_TOKEN = os.getenv("SHOPIFY_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
assert all([SHOPIFY_SHOP, SHOPIFY_TOKEN, OPENAI_API_KEY]), "Missing one or more required .env values!"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

CSV_FIELDNAMES = [
    "Handle", "Title", "Body (HTML)", "Vendor", "Tags", "Published",
    "Option1 Name", "Option1 Value", "Variant Inventory Qty", "Variant Price", "Image Src"
]


# --- 1. Get all image URLs from Shopify Files API ---
def get_shopify_images():
    """Fetches all image file URLs from Shopify Files API using GraphQL."""
    url = f"https://{SHOPIFY_SHOP}/admin/api/2025-04/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
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
        try:
            result = response.json()
        except Exception as ex:
            print("Failed to parse JSON response:", response.text)
            raise
        # Error handling
        if "errors" in result:
            print("Shopify API returned error(s):", result["errors"])
            raise Exception("Shopify GraphQL query failed.")
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


# --- 2. Parse image filenames and create product objects ---
def parse_image_filename(filename):
    """
    Expects: category_subcat1_subcat2_Title_Price.png
    Example: video-games_atari_consoles_Atari-2600_89.99.png
    """
    name = os.path.splitext(os.path.basename(filename))[0]
    parts = name.split('_')
    if len(parts) < 4:
        raise ValueError(f"Filename too short: {filename}")
    try:
        price = float(parts[-1])
    except Exception:
        raise ValueError(f"Price part must be a float, got: {parts[-1]} in {filename}")
    title_raw = parts[-2]
    title = title_raw.replace('-', ' ').title()
    categories = parts[:-2]
    base_handle = "-".join(parts[:-1]).lower()
    # Salt: 6-char hash from filename for uniqueness
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
    }


# --- 3. AI-powered product description ---
def get_ai_description(title, tags, image_url):
    prompt = (
        f"You are a master copywriter for a hip and upcoming retro reseller brand. "
        f"Write a 30-word product description for an online retro shop.\n"
        f"Product name: {title}\nTags: {', '.join(tags)}\n"
        f"Be accurate and appealing, avoid repeating the tags. Fitting a retro brand. "
        f"Here is the main image: {image_url}"
    )
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


# --- 4. Group images by handle, build product dicts for CSV and JS ---
def group_images_by_handle(images):
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
        desc = get_ai_description(title, tags, img["url"])
        # JS Product object (for your site)
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
        # Shopify CSV row
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


# --- 5. Write Shopify CSV ---
def write_csv(products, outfile):
    with open(outfile, "w", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for prod in products:
            writer.writerow(prod["csv_row"])
    print(f"Wrote {len(products)} products to {outfile}")


# --- 6. Write products.js for your frontend ---
def write_products_js(products, outfile):
    product_list = [prod["js_product"] for prod in products]
    with open(outfile, "w", encoding="utf-8") as f:
        f.write("window.products = ")
        json.dump(product_list, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"Wrote {len(product_list)} products to {outfile}")


# --- MAIN ---
if __name__ == "__main__":
    all_images = get_shopify_images()
    products = group_images_by_handle(all_images)
    write_csv(products, "shopify_upload.csv")
    write_products_js(products, "products.js")
