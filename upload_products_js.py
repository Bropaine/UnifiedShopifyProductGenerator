import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import paramiko
import threading
import webbrowser
from dotenv import load_dotenv

# --- Load .env for defaults ---
load_dotenv()
DEFAULT_HOST = os.getenv("SFTP_HOST", "")
DEFAULT_PORT = os.getenv("SFTP_PORT", "22")
DEFAULT_USER = os.getenv("SFTP_USER", "")
DEFAULT_PASS = os.getenv("SFTP_PASS", "")
DEFAULT_REMOTE_PATH = os.getenv("REMOTE_PRODUCTS_PATH", "")
DEFAULT_LOCAL_FILE = "products.js"
REMOTE_VIEW_URL = os.getenv("REMOTE_PRODUCTS_VIEW_URL", "")  # Optional: e.g. https://yoursite.com/assets/products.js

class SFTPUploaderGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SFTP products.js Uploader")
        self.geometry("550x370")
        instructions = (
            "How to use:\n"
            "1. Ensure products.js (final version) exists in this folder.\n"
            "2. Confirm SFTP credentials below (from .env, can be edited).\n"
            "3. Click 'Upload products.js'.\n"
            "4. You may open your live site after upload to verify."
        )
        tk.Label(self, text=instructions, justify="left", wraplength=520).pack(pady=7)

        frm = tk.Frame(self)
        frm.pack(pady=5, fill='x')

        # Local file input (locked for now)
        tk.Label(frm, text="Local file:").grid(row=0, column=0, sticky='e')
        self.local_file = tk.StringVar(value=DEFAULT_LOCAL_FILE)
        tk.Entry(frm, textvariable=self.local_file, width=38, state="readonly").grid(row=0, column=1, padx=2)

        tk.Label(frm, text="SFTP Host:").grid(row=1, column=0, sticky='e')
        self.host_entry = tk.Entry(frm, width=38)
        self.host_entry.grid(row=1, column=1, padx=2)
        self.host_entry.insert(0, DEFAULT_HOST)

        tk.Label(frm, text="Port:").grid(row=2, column=0, sticky='e')
        self.port_entry = tk.Entry(frm, width=38)
        self.port_entry.grid(row=2, column=1, padx=2)
        self.port_entry.insert(0, DEFAULT_PORT)

        tk.Label(frm, text="Username:").grid(row=3, column=0, sticky='e')
        self.user_entry = tk.Entry(frm, width=38)
        self.user_entry.grid(row=3, column=1, padx=2)
        self.user_entry.insert(0, DEFAULT_USER)

        tk.Label(frm, text="Password:").grid(row=4, column=0, sticky='e')
        self.pass_entry = tk.Entry(frm, width=38, show="*")
        self.pass_entry.grid(row=4, column=1, padx=2)
        self.pass_entry.insert(0, DEFAULT_PASS)

        tk.Label(frm, text="Remote path:").grid(row=5, column=0, sticky='e')
        self.remote_path_entry = tk.Entry(frm, width=38)
        self.remote_path_entry.grid(row=5, column=1, padx=2)
        self.remote_path_entry.insert(0, DEFAULT_REMOTE_PATH)

        self.upload_btn = tk.Button(self, text="Upload products.js", command=self.upload_clicked)
        self.upload_btn.pack(pady=13)

        self.status = tk.Label(self, text="", fg="blue", wraplength=500)
        self.status.pack()

        self.link = None  # For post-upload hyperlink

    def upload_clicked(self):
        local_file = self.local_file.get()
        host = self.host_entry.get().strip()
        port = self.port_entry.get().strip()
        user = self.user_entry.get().strip()
        pw = self.pass_entry.get()
        remote_path = self.remote_path_entry.get().strip()

        if not all([host, port, user, pw, remote_path, local_file]):
            messagebox.showerror("Missing info", "Please complete all credential fields.")
            return

        if not os.path.isfile(local_file):
            messagebox.showerror("File not found", f"Could not find '{local_file}' in this folder.")
            return

        self.status.config(text="Uploading...", fg="#176ad4")
        self.upload_btn.config(state="disabled")
        if self.link:
            self.link.destroy()
            self.link = None
        threading.Thread(
            target=self.do_upload,
            args=(host, port, user, pw, local_file, remote_path),
            daemon=True
        ).start()

    def do_upload(self, host, port, user, pw, local_file, remote_path):
        try:
            port = int(port)
            self.set_status(f"Connecting to {host}:{port}...", "#176ad4")
            transport = paramiko.Transport((host, port))
            transport.connect(username=user, password=pw)
            sftp = paramiko.SFTPClient.from_transport(transport)
            self.set_status(f"Uploading {local_file} to {remote_path} ...", "#176ad4")
            sftp.put(local_file, remote_path)
            sftp.close()
            transport.close()
            self.set_status("Upload complete! ✅", "#298e46")
            self.show_link()
        except Exception as ex:
            self.set_status(f"Upload failed: {ex}", "#b03030")
        finally:
            self.upload_btn.config(state="normal")

    def set_status(self, msg, color):
        self.status.config(text=msg, fg=color)

    def show_link(self):
        url = REMOTE_VIEW_URL
        if url:
            if self.link:
                self.link.destroy()
            self.link = tk.Label(self, text="Open products.js on your live site", fg="#176ad4", cursor="hand2", wraplength=500)
            self.link.pack()
            self.link.bind("<Button-1>", lambda e: webbrowser.open(url))


if __name__ == "__main__":
    SFTPUploaderGUI().mainloop()
