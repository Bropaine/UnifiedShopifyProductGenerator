import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
from Valid_Category_Paths.valid_category_paths import VALID_CATEGORY_PATHS

class FilenameSuggester(tk.Tk):
    def __init__(self, valid_paths):
        super().__init__()
        self.title("Product Filename Suggester")
        self.valid_paths = valid_paths
        self.selected_cats = []
        self.dropdown_vars = []
        self.dropdown_widgets = []

        tk.Label(self, text="Choose Category Path:").pack(pady=3)
        self.category_frame = tk.Frame(self)
        self.category_frame.pack()

        # Title, price, notes fields
        self.title_var = tk.StringVar()
        self.price_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.preview_var = tk.StringVar()

        tk.Label(self, text="Product Title (e.g., Super-Mario-Bros)").pack(pady=2)
        tk.Entry(self, textvariable=self.title_var).pack()

        tk.Label(self, text="Price (e.g., 49.99)").pack(pady=2)
        tk.Entry(self, textvariable=self.price_var).pack()

        tk.Label(self, text="Extra Notes (optional, e.g., sealed-in-box)").pack(pady=2)
        tk.Entry(self, textvariable=self.notes_var).pack()

        tk.Label(self, text="Suggested Filename:").pack(pady=2)
        tk.Entry(self, textvariable=self.preview_var, state="readonly", width=80).pack(pady=5)

        tk.Button(self, text="Copy Filename", command=self.copy_to_clipboard).pack(pady=2)

        # Traces for filename updates
        self.title_var.trace_add('write', lambda *_: self.update_preview())
        self.price_var.trace_add('write', lambda *_: self.update_preview())
        self.notes_var.trace_add('write', lambda *_: self.update_preview())

        self.build_cascading_dropdowns([])  # Start with root

    def build_cascading_dropdowns(self, selected_path):
        # Remove any dropdowns beyond this level
        for widget in self.dropdown_widgets[len(selected_path):]:
            widget.destroy()
        self.dropdown_widgets = self.dropdown_widgets[:len(selected_path)]
        self.dropdown_vars = self.dropdown_vars[:len(selected_path)]

        # Figure out next possible options based on current selection
        options = set()
        for path in self.valid_paths:
            if tuple(path[:len(selected_path)]) == tuple(selected_path):
                if len(path) > len(selected_path):
                    options.add(path[len(selected_path)])
        options = sorted(options)
        if not options:
            self.selected_cats = selected_path
            self.update_preview()
            return

        # Make next dropdown
        var = tk.StringVar()
        self.dropdown_vars.append(var)
        frame = tk.Frame(self.category_frame)
        frame.pack(side='left', padx=3)
        cb = ttk.Combobox(frame, values=options, textvariable=var, state="readonly", width=18)
        cb.pack()
        self.dropdown_widgets.append(frame)

        def on_select(event=None):
            new_path = selected_path + [var.get()]
            self.build_cascading_dropdowns(new_path)

        cb.bind("<<ComboboxSelected>>", on_select)
        # If you are resetting, set variable to blank
        var.set("")
        self.selected_cats = selected_path
        self.update_preview()

    def get_selected_cat_path(self):
        # Collects all selected values from all dropdowns in order
        values = []
        for var in self.dropdown_vars:
            v = var.get()
            if not v:
                break
            values.append(v)
        return values

    def update_preview(self):
        cat_path = self.get_selected_cat_path()
        if not cat_path:
            self.preview_var.set("")
            return
        title = self.title_var.get().replace(" ", "-")
        price = self.price_var.get()
        notes = self.notes_var.get().replace(" ", "-")
        parts = list(cat_path)
        if title:
            parts.append(title)
        if price:
            parts.append(price)
        if notes:
            parts.append(notes)
        filename = "_".join(parts) + ".png"
        self.preview_var.set(filename)

    def copy_to_clipboard(self):
        fn = self.preview_var.get()
        if not fn:
            messagebox.showwarning("No Filename", "No filename to copy. Please select categories and fill out the form.")
            return
        pyperclip.copy(fn)
        messagebox.showinfo("Copied", f"Filename copied to clipboard:\n\n{fn}")

if __name__ == "__main__":
    app = FilenameSuggester(VALID_CATEGORY_PATHS)
    app.mainloop()
