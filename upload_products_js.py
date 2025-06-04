"""
Automated SFTP Uploader for products.js (Namecheap or Any cPanel Host)
----------------------------------------------------------------------
Uploads the latest products.js file to your Namecheap (or other cPanel) server
after you've generated and updated product data.

This is the final step in your human-in-the-loop workflow:
    1. Generate products.js and CSV (main.py)
    2. Import CSV and backfill variant IDs (backfill_variant_ids.py)
    3. Upload products.js to your website (this script)

All SFTP credentials and remote path are loaded from .env for security and consistency.

**IMPORTANT:** This script does not remove or overwrite any other files—only uploads products.js.
"""

import os
import paramiko
from dotenv import load_dotenv

# --- Load .env SFTP credentials ---
load_dotenv()
host = os.getenv("SFTP_HOST")
port = int(os.getenv("SFTP_PORT", "22"))
username = os.getenv("SFTP_USER")
password = os.getenv("SFTP_PASS")
remote_path = os.getenv("REMOTE_PRODUCTS_PATH")
local_file = "products.js"

if not all([host, port, username, password, remote_path]):
    raise Exception("Missing one or more SFTP environment variables in .env.")


# --- SFTP upload ---
def upload_file(local_path, remote_path):
    transport = paramiko.Transport((host, port))
    try:
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        print(f"Uploading {local_path} to {remote_path} ...")
        sftp.put(local_path, remote_path)
        print("Upload complete.")
        sftp.close()
    finally:
        transport.close()


if __name__ == "__main__":
    upload_file(local_file, remote_path)
