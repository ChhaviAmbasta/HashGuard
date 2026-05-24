import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import hashlib
import os
from datetime import datetime
import sqlite3

current_user = ""

def open_dashboard(username):

    global current_user

    current_user = username

    root.mainloop()

# ================= WINDOW =================
root = tk.Tk()
root.title("HashGuard Dashboard")
root.geometry("1250x720")
root.configure(bg="#0b1437")


# ================= DATABASE =================
conn = sqlite3.connect("database/files.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT,
    file_size TEXT,
    file_hash TEXT UNIQUE,
    uploaded_by TEXT,
    upload_time TEXT
)
""")

conn.commit()

# ================= HEADER =================
header = tk.Frame(root, bg="#111c44", height=90)
header.pack(fill="x")

title = tk.Label(
    header,
    text="HashGuard Dashboard",
    font=("Segoe UI", 30, "bold"),
    fg="white",
    bg="#111c44"
)
title.pack(pady=20)

# ================= BUTTON FRAME =================
button_frame = tk.Frame(root, bg="#0b1437")
button_frame.pack(pady=20)

# ================= HASH FUNCTION =================
def generate_hash(file_path):

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while chunk := file.read(4096):
            sha256.update(chunk)

    return sha256.hexdigest()

# ================= STATUS LABEL =================
status_label = tk.Label(
    root,
    text="System Ready",
    font=("Segoe UI", 11, "bold"),
    fg="#cbd5e1",
    bg="#0b1437"
)
status_label.pack(pady=(0, 10))

# ================= TABLE CONTAINER =================
table_container = tk.Frame(
    root,
    bg="white"
)
table_container.pack(
    fill="both",
    expand=True,
    padx=25,
    pady=10
)

# ================= TABLE TITLE =================
table_title = tk.Label(
    table_container,
    text="Uploaded Files",
    font=("Segoe UI", 20, "bold"),
    fg="#111827",
    bg="white"
)
table_title.pack(anchor="w", padx=20, pady=15)

# ================= TABLE =================
columns = (
    "File Name",
    "Size",
    "SHA-256 Hash",
    "Uploaded By",
    "Date & Time"
)

style = ttk.Style()

style.theme_use("default")

style.configure(
    "Treeview",
    background="white",
    foreground="black",
    rowheight=34,
    fieldbackground="white",
    borderwidth=0,
    font=("Segoe UI", 10)
)

style.configure(
    "Treeview.Heading",
    background="#4f46e5",
    foreground="white",
    font=("Segoe UI", 11, "bold")
)

tree = ttk.Treeview(
    table_container,
    columns=columns,
    show="headings",
    height=15
)

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=240)

tree.pack(fill="both", expand=True, padx=20, pady=10)

# ================= LOAD FILES =================
def load_files():

    cursor.execute("SELECT * FROM files")

    rows = cursor.fetchall()

    for row in rows:

        tree.insert(
            "",
            "end",
            values=(
                row[1],
                row[2],
                row[3][:30] + "...",
                row[4],
                row[5]
            )
        )

# ================= UPLOAD FILE =================
def upload_file():

    file_path = filedialog.askopenfilename()

    if not file_path:
        return

    try:

        file_name = os.path.basename(file_path)

        file_size = round(
            os.path.getsize(file_path) / 1024,
            2
        )

        file_hash = generate_hash(file_path)

        upload_time = datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )

        # Duplicate Check
        cursor.execute(
            "SELECT * FROM files WHERE file_hash=?",
            (file_hash,)
        )

        existing_file = cursor.fetchone()

        if existing_file:

            status_label.config(
                text="Duplicate File Detected",
                fg="orange"
            )

            messagebox.showwarning(
                "Duplicate File",
                "This file already exists"
            )

            return

        # Save to Database
        cursor.execute(
            """
            INSERT INTO files (
                file_name,
                file_size,
                file_hash,
                uploaded_by,
                upload_time
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                file_name,
                f"{file_size} KB",
                file_hash,
                current_user,
                upload_time
            )
        )

        conn.commit()

        # Show in Table
        tree.insert(
            "",
            "end",
            values=(
                file_name,
                f"{file_size} KB",
                file_hash[:30] + "...",
                current_user,
                upload_time
            )
        )

        status_label.config(
            text="File Uploaded Successfully",
            fg="#22c55e"
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

# ================= VERIFY FILE =================
def verify_file():

    file_path = filedialog.askopenfilename()

    if not file_path:
        return

    try:

        file_name = os.path.basename(file_path)

        current_hash = generate_hash(file_path)

        cursor.execute(
            "SELECT file_hash FROM files WHERE file_name=?",
            (file_name,)
        )

        result = cursor.fetchone()

        if result is None:

            status_label.config(
                text="File Not Found In Database",
                fg="red"
            )

            return

        stored_hash = result[0]

        # Compare Hash
        if current_hash == stored_hash:

            status_label.config(
                text="File Integrity Verified",
                fg="#22c55e"
            )

            messagebox.showinfo(
                "Verified",
                "File Integrity Verified"
            )

        else:

            status_label.config(
                text="File Tampered",
                fg="red"
            )

            messagebox.showerror(
                "Tampered",
                "File Has Been Modified"
            )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

# ================= BUTTONS =================
upload_btn = tk.Button(
    button_frame,
    text="Upload File",
    font=("Segoe UI", 12, "bold"),
    bg="#4f46e5",
    fg="white",
    padx=35,
    pady=12,
    borderwidth=0,
    cursor="hand2",
    command=upload_file
)

upload_btn.grid(
    row=0,
    column=0,
    padx=15
)

verify_btn = tk.Button(
    button_frame,
    text="Verify File",
    font=("Segoe UI", 12, "bold"),
    bg="#16a34a",
    fg="white",
    padx=35,
    pady=12,
    borderwidth=0,
    cursor="hand2",
    command=verify_file
)

verify_btn.grid(
    row=0,
    column=1,
    padx=15
)

# ================= LOAD SAVED FILES =================
load_files()

# ================= FOOTER =================
footer = tk.Label(
    root,
    text="HashGuard | Secure File Integrity System",
    font=("Segoe UI", 10),
    fg="#cbd5e1",
    bg="#0b1437"
)

footer.pack(pady=10)

