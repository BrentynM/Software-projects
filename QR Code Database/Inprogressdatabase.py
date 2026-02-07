import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime
import os

# --- DATABASE LAYER ---
class DatabaseManager:
    def __init__(self, db_name="inventory.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS items 
            (barcode TEXT PRIMARY KEY, name TEXT, category TEXT, quantity INTEGER, date_added TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, barcode TEXT, action TEXT, qty_change INTEGER, timestamp TEXT, reason TEXT)''')
        self.conn.commit()

    def add_item(self, barcode, name, category, qty=1):
        try:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.cursor.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?)", (barcode, name, category, qty, date_str))
            self.log_transaction(barcode, "REGISTER", qty, "Initial Stock")
            self.conn.commit()
            return True
        except sqlite3.IntegrityError: 
            return False

    def update_quantity(self, barcode, adjust, reason):
        self.cursor.execute("SELECT quantity FROM items WHERE barcode=?", (barcode,))
        res = self.cursor.fetchone()
        if res:
            new_qty = max(0, res[0] + adjust)
            self.cursor.execute("UPDATE items SET quantity = ? WHERE barcode = ?", (new_qty, barcode))
            self.log_transaction(barcode, "ADJUST", adjust, reason)
            self.conn.commit()
            return new_qty
        return 0

    def log_transaction(self, barcode, action, qty, reason):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO transactions (barcode, action, qty_change, timestamp, reason) VALUES (?, ?, ?, ?, ?)",
                            (barcode, action, qty, ts, reason))

    def delete_item(self, barcode):
        self.cursor.execute("DELETE FROM items WHERE barcode = ?", (barcode,))
        self.log_transaction(barcode, "DELETE", 0, "Item Removed")
        self.conn.commit()

    def fetch_all(self, search=""):
        q = "SELECT * FROM items WHERE name LIKE ? OR barcode LIKE ? OR category LIKE ?"
        self.cursor.execute(q, (f'%{search}%', f'%{search}%', f'%{search}%'))
        return self.cursor.fetchall()

# --- GUI LAYER ---
class InventoryApp:
    def __init__(self, root):
        self.db = DatabaseManager()
        self.root = root
        self.root.title("Pi 5 Inventory - TTU CS Edition")
        self.root.geometry("1000x700")
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=35, font=("Arial", 11))

        self.notebook = ttk.Notebook(root)
        self.tab_scan = ttk.Frame(self.notebook)
        self.tab_view = ttk.Frame(self.notebook)
        self.tab_hist = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_scan, text=" [1] SCANNER ")
        self.notebook.add(self.tab_view, text=" [2] MANAGE ")
        self.notebook.add(self.tab_hist, text=" [3] HISTORY ")
        self.notebook.pack(expand=1, fill="both")

        self.setup_scan_tab()
        self.setup_view_tab()
        self.setup_hist_tab()

        self.stats_label = tk.Label(root, text="", bd=1, relief="sunken", anchor="w")
        self.stats_label.pack(side="bottom", fill="x")
        self.refresh_table()

    def setup_scan_tab(self):
        self.img_container = tk.Label(self.tab_scan, text="[ Image Area ]", bg="#dfe6e9", width=40, height=12)
        self.img_container.pack(pady=20)
        self.status_label = tk.Label(self.tab_scan, text="READY TO SCAN", font=("Arial", 20, "bold"))
        self.status_label.pack(pady=10)
        self.barcode_entry = tk.Entry(self.tab_scan, font=("Arial", 1), bd=0)
        self.barcode_entry.pack()
        self.barcode_entry.bind('<Return>', self.handle_scan)
        self.barcode_entry.focus_set()

    def setup_view_tab(self):
        top = tk.Frame(self.tab_view)
        top.pack(fill="x", padx=10, pady=10)
        
        # Search Box
        tk.Label(top, text="🔍 Search:").pack(side="left", padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_table())
        tk.Entry(top, textvariable=self.search_var, width=15).pack(side="left", padx=5)
        
        # --- NEW: QUICK ADJUST PANEL ---
        adj_group = tk.LabelFrame(top, text=" Quick Stock Adjust ", padx=10, pady=5)
        adj_group.pack(side="left", padx=20)
        
        ttk.Button(adj_group, text="➖", width=4, command=lambda: self.quick_adjust(-1)).pack(side="left", padx=2)
        ttk.Button(adj_group, text="➕", width=4, command=lambda: self.quick_adjust(1)).pack(side="left", padx=2)
        ttk.Button(adj_group, text="Custom +/-", command=self.custom_adjust).pack(side="left", padx=5)

        # Action Buttons
        ttk.Button(top, text="🔄 REFRESH", command=self.refresh_table).pack(side="right", padx=5)
        ttk.Button(top, text="DELETE SELECTED", command=self.delete_selected).pack(side="right")

        cols = ("barcode", "name", "category", "qty", "date")
        self.tree = ttk.Treeview(self.tab_view, columns=cols, show="headings")
        for c in cols: 
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=100)
            
        self.tree.tag_configure('low', background='#ffcccc')
        self.tree.pack(expand=True, fill="both", padx=10)

    def setup_hist_tab(self):
        cols = ("id", "barcode", "action", "change", "time", "reason")
        self.hist_tree = ttk.Treeview(self.tab_hist, columns=cols, show="headings")
        for c in cols: 
            self.hist_tree.heading(c, text=c.upper())
        self.hist_tree.pack(expand=True, fill="both", padx=10, pady=10)
        ttk.Button(self.tab_hist, text="REFRESH HISTORY", command=self.refresh_history).pack(pady=5)

    # --- LOGIC METHODS ---

    def handle_scan(self, event):
        barcode = self.barcode_entry.get().strip()
        self.barcode_entry.delete(0, tk.END)
        if not barcode: return

        self.db.cursor.execute("SELECT name, quantity FROM items WHERE barcode=?", (barcode,))
        res = self.db.cursor.fetchone()

        if res:
            name, qty = res
            adj = simpledialog.askinteger("Update", f"{name} (Current Stock: {qty})\nAdjustment (+/-):", initialvalue=-1)
            if adj is not None:
                reason = simpledialog.askstring("Reason", "Note:", initialvalue="Scanner Adjustment")
                self.db.update_quantity(barcode, adj, reason or "Manual")
        else:
            self.prompt_new(barcode)
        
        self.refresh_table()
        self.barcode_entry.focus_set()

    def quick_adjust(self, amount):
        """Adjusts selected row by amount without a popup dialog."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select an item in the list first.")
            return
        
        item_vals = self.tree.item(selection[0])['values']
        barcode = str(item_vals[0])
        reason = "Quick Add" if amount > 0 else "Quick Remove"
        
        self.db.update_quantity(barcode, amount, reason)
        self.refresh_table()

    def custom_adjust(self):
        """Triggered from the Manage tab to allow a typed number for selected item."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Please select an item in the list first.")
            return
            
        item_vals = self.tree.item(selection[0])['values']
        barcode = str(item_vals[0])
        name = item_vals[1]
        
        adj = simpledialog.askinteger("Bulk Adjust", f"Adjust stock for: {name}\nEnter positive or negative number:")
        if adj is not None:
            reason = simpledialog.askstring("Reason", "Note:", initialvalue="Manual Adjustment")
            self.db.update_quantity(barcode, adj, reason or "Manual")
            self.refresh_table()

    def prompt_new(self, barcode):
        d = tk.Toplevel(self.root)
        d.title("Register New Item")
        d.geometry("300x250")
        tk.Label(d, text=f"New Barcode Detected: {barcode}", fg="blue").pack(pady=10)
        
        tk.Label(d, text="Item Name:").pack()
        name_e = tk.Entry(d); name_e.pack(pady=2)
        
        tk.Label(d, text="Category:").pack()
        cat_c = ttk.Combobox(d, values=["Sensors", "Boards", "Cables", "Tools", "Mechanical"]); 
        cat_c.set("Sensors"); cat_c.pack(pady=2)
        
        tk.Label(d, text="Initial Quantity:").pack()
        qty_e = tk.Entry(d); qty_e.insert(0, "1"); qty_e.pack(pady=2)

        def save():
            try:
                q = int(qty_e.get())
                self.db.add_item(barcode, name_e.get(), cat_c.get(), q)
                d.destroy()
                self.refresh_table()
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a number.")
                
        tk.Button(d, text="✅ SAVE ITEM", command=save, bg="#55efc4").pack(pady=15)

    def delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Error", "Select an item first!")
            return
        
        item_vals = self.tree.item(selection[0])['values']
        barcode = str(item_vals[0])
        
        if messagebox.askyesno("Delete", f"Are you sure you want to permanently delete {item_vals[1]}?\nThis removes all records of this barcode."):
            self.db.delete_item(barcode)
            self.refresh_table()

    def refresh_history(self):
        for i in self.hist_tree.get_children(): self.hist_tree.delete(i)
        self.db.cursor.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT 50")
        for r in self.db.cursor.fetchall(): self.hist_tree.insert("", tk.END, values=r)

    def refresh_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in self.db.fetch_all(self.search_var.get()):
            # Low stock warning if quantity < 2
            tag = ('low',) if r[3] < 2 else ()
            self.tree.insert("", tk.END, values=r, tags=tag)
        
        # Update Footer Stats
        self.db.cursor.execute("SELECT COUNT(*), SUM(quantity) FROM items")
        s = self.db.cursor.fetchone()
        self.stats_label.config(text=f"  Inventory Summary | Unique Items: {s[0]} | Total Units in Stock: {s[1] or 0}")
        self.refresh_history()

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    # Ensure scanning focus
    root.bind("<Button-1>", lambda e: app.barcode_entry.focus_set())
    root.mainloop()
