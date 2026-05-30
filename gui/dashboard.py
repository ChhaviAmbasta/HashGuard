import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import hashlib
import os
from datetime import datetime
import sqlite3
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
import shutil
from PIL import Image, ImageTk
import random

current_user = ""

def open_dashboard(username):

    global current_user

    current_user = username

    root.mainloop()

# ================= WINDOW =================
root = tk.Tk()
root.title("HashGuard Dashboard")
root.geometry("1250x720")
root.minsize(1200, 700)
root.configure(bg="#0b1437")

# ================= PARTICLE BACKGROUND =================

canvas = tk.Canvas(
    root,
    bg="#0b1437",
    highlightthickness=0
)

canvas.place(
    relwidth=1,
    relheight=1
)

particles = []

for i in range(220):

    x = random.randint(0, 2000)

    y = random.randint(0, 1200)

    size = random.randint(2, 5)

    colors = [
        "#22d3ee",
        "#38bdf8",
        "#67e8f9",
        "#0ea5e9"
    ]

    particle = canvas.create_oval(
        x,
        y,
        x + size,
        y + size,
        fill=random.choice(colors),
        outline=""
    )

    dx = random.choice([-1, 1]) * random.uniform(0.3, 0.8)
    dy = random.choice([-1, 1]) * random.uniform(0.3, 0.8)

    particles.append([particle, dx, dy])

# ================= PARTICLE ANIMATION =================

def animate_particles():

    width = root.winfo_width()
    height = root.winfo_height()

    for particle_data in particles:

        particle = particle_data[0]
        dx = particle_data[1]
        dy = particle_data[2]

        canvas.move(particle, dx, dy)

        x1, y1, x2, y2 = canvas.coords(particle)

        if x1 <= 0 or x2 >= width:
            particle_data[1] *= -1

        if y1 <= 0 or y2 >= height:
            particle_data[2] *= -1

    root.after(35, animate_particles)

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
    upload_time TEXT,
    status TEXT,
    file_path TEXT,
    permission TEXT
)
""")

conn.commit()

# ================= HEADER =================
header = tk.Frame(root, bg="#111c44", height=110)
header.pack(fill="x")

logo_img = Image.open("assets/HashGuard_logo.png")

logo_img = logo_img.resize((60, 70))

logo = ImageTk.PhotoImage(logo_img)

logo_label = tk.Label(
    header,
    image=logo,
    bg="#111c44",
    bd=0,
    highlightthickness=0
)

logo_label.image = logo

logo_label.place(x=25, y=10)

title = tk.Label(
    header,
    text="HashGuard Dashboard",
    font=("Segoe UI", 26, "bold"),
    fg="white",
    bg="#111c44"
)
title.pack(pady=20)

# ================= BUTTON FRAME =================
button_frame = tk.Frame(root, bg="#0b1437")
button_frame.pack(pady=20)

# ================= SEARCH FUNCTION =================

def search_file():

    search = search_entry.get().lower()

    for item in tree.get_children():

        values = tree.item(item)["values"]

        if search in str(values[0]).lower():

            tree.selection_set(item)
            tree.focus(item)

            break

# ================= SEARCH BAR =================

search_frame = tk.Frame(root, bg="#0b1437")
search_frame.pack(pady=10)

search_entry = tk.Entry(
    search_frame,
    font=("Segoe UI", 11),
    width=30
)

search_entry.grid(row=0, column=0, padx=10)

search_btn = tk.Button(
    search_frame,
    text="Search",
    command=search_file,
    font=("Segoe UI", 10, "bold"),
    bg="#4f46e5",
    fg="white",
    padx=15,
    pady=5,
    borderwidth=0,
    cursor="hand2"
)

search_btn.grid(row=0, column=1)

# ================= LOGOUT FUNCTION =================

def logout():

    root.destroy()

    import login

# ================= LOGOUT BUTTON =================

logout_btn = tk.Button(
    header,
    text="Logout",
    command=logout,
    font=("Segoe UI", 10, "bold"),
    bg="#dc2626",
    fg="white",
    padx=15,
    pady=5,
    borderwidth=0,
    cursor="hand2"
)

logout_btn.place(
    relx=0.98,
    y=25,
    anchor="ne"
)

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
    "Date & Time",
    "Status"
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

tree.column("File Name", width=220)
tree.column("Size", width=100)
tree.column("SHA-256 Hash", width=280)
tree.column("Uploaded By", width=120)
tree.column("Date & Time", width=170)
tree.column("Status", width=120)

tree.tag_configure(
    "verified",
    background="#dcfce7"
)

tree.tag_configure(
    "tampered",
    background="#fee2e2"
)

scrollbar = ttk.Scrollbar(
    table_container,
    orient="vertical",
    command=tree.yview
)

tree.configure(
    yscrollcommand=scrollbar.set
)

scrollbar.pack(
    side="right",
    fill="y"
)

tree.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10,
    side="left"
)

# ================= FILE COUNT =================

count_label = tk.Label(
    root,
    text="Total Files: 0",
    font=("Segoe UI", 11, "bold"),
    fg="white",
    bg="#0b1437"
)

count_label.pack(pady=5, before=table_container)


# ================= LOAD FILES =================
def load_files():

    tree.delete(*tree.get_children())

    cursor.execute("SELECT * FROM files")

    rows = cursor.fetchall()

    for row in rows:

        status = row[6]

        tag = ""

        if status == "Verified":
            tag = "verified"

        elif status == "Tampered":
            tag = "tampered"

        tree.insert(
            "",
            "end",
            values=(
                row[1],
                row[2],
                row[3][:30] + "...",
                row[4],
                row[5],
                row[6]
            ),
            tags=(tag,)
        )

    count_label.config(
        text=f"Total Files: {len(tree.get_children())}"
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
        print("HASH:", file_hash)

        upload_time = datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )

        # Create uploads folder if not exists
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
            
        # Copy file to uploads folder
        destination = os.path.join("uploads", file_name)
        shutil.copy(file_path, destination)

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
            upload_time,
            status,
            file_path,
            permission
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                
                    file_name,
                    f"{file_size} KB",
                    file_hash,
                    current_user,
                    upload_time,
                    "Pending",
                    destination,
                    "Owner"
)
        )

        conn.commit()

        # Reload Table
        load_files()

        status_label.config(
            text="File Uploaded Successfully",
            fg="#22c55e"
        )

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

def open_file():

    selected = tree.focus()

    if not selected:
        messagebox.showwarning("Warning", "Please select a file")
        return

    values = tree.item(selected, "values")

    filename = values[0]

    cursor.execute(
        "SELECT uploaded_by FROM files WHERE file_name=?",
        (filename,)
        )
    
    owner = cursor.fetchone()[0]
    
    if owner != current_user:
        messagebox.showerror(
            "Access Denied",
            "You can only open your own files"
            )
        return

    filepath = os.path.join("uploads", filename)

    if os.path.exists(filepath):
        os.startfile(filepath)
    else:
        messagebox.showerror("Error", "File not found")

# ================= VERIFY FILE =================
def verify_file():

    selected = tree.selection()

    if not selected:

        messagebox.showwarning(
            "No Selection",
            "Please select a file"
        )

        return

    values = tree.item(selected)["values"]

    filename = values[0]

    filepath = os.path.join("uploads", filename)

    if not os.path.exists(filepath):

        messagebox.showerror(
            "Error",
            "File not found"
        )

        return

    current_hash = generate_hash(filepath)

    cursor.execute(
        "SELECT id, file_hash, uploaded_by FROM files WHERE file_name=?",
        (filename,)
    )

    result = cursor.fetchone()

    if not result:

        messagebox.showerror(
            "Error",
            "File not found in database"
        )

        return

    file_id = result[0]
    
    stored_hash = result[1]
    
    owner = result[2]

    if owner != current_user:
        
        messagebox.showerror(
            "Access Denied",
            "You can only verify your own files"
            
            )
        return


    if current_hash == stored_hash:

        status = "Verified"

        status_label.config(
            text="File Integrity Verified",
            fg="#22c55e"
        )

        messagebox.showinfo(
            "Verified",
            "File Integrity Verified"
        )

    else:

        status = "Tampered"

        status_label.config(
            text="File Tampered",
            fg="red"
        )

        messagebox.showerror(
            "Tampered",
            "File Has Been Modified"
        )

    cursor.execute(
        "UPDATE files SET status=? WHERE id=?",
        (status, file_id)
    )

    conn.commit()

    load_files()

open_btn = tk.Button(
    button_frame,
    text="Open File",
    command=open_file,
    bg="#ebde25",
    fg="white",
    font=("Segoe UI", 12, "bold"),
    width=15,
    height=2,
    relief="flat",
    cursor="hand2"
)

open_btn.grid(row=0, column=4, padx=15)

# ================= DELETE FILE =================

def delete_file():

    selected_item = tree.selection()

    if not selected_item:

        messagebox.showwarning(
            "No Selection",
            "Please select a file to delete"
        )

        return

    values = tree.item(selected_item)["values"]

    file_name = values[0]

    cursor.execute(
    "SELECT uploaded_by FROM files WHERE file_name=?",
    (file_name,)
)
    owner = cursor.fetchone()[0]
    if owner != current_user:
        messagebox.showerror(
            "Access Denied",
            "You can only delete your own files"
            )
        return

    confirm = messagebox.askyesno(
        "Delete File",
        f"Are you sure you want to delete:\n{file_name} ?"
    )

    if confirm:

        cursor.execute(
            "DELETE FROM files WHERE file_name=?",
            (file_name,)
        )

        conn.commit()

        load_files()

        status_label.config(
            text="File Deleted Successfully",
            fg="red"
        )

# ================= EXPORT REPORT =================

def export_pdf():

    cursor.execute("SELECT * FROM files")

    rows = cursor.fetchall()

    if not rows:

        messagebox.showwarning(
            "No Data",
            "No files available to export"
        )

        return

    pdf = SimpleDocTemplate(
        "HashGuard_Report.pdf",
        pagesize=letter
    )

    data = [
        [
            "File Name",
            "Size",
            "Uploaded By",
            "Date & Time"
        ]
    ]

    for row in rows:

        data.append([
            row[1],
            row[2],
            row[4],
            row[5]
        ])

    table = Table(data)

    style = TableStyle([

        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),

        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),

        ('GRID', (0, 0), (-1, -1), 1, colors.black),

        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),

        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),

        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke)

    ])

    table.setStyle(style)

    elements = [table]

    pdf.build(elements)

    status_label.config(
        text="Report Exported Successfully",
        fg="#22c55e"
    )

    messagebox.showinfo(
        "Success",
        "Report Saved as HashGuard_Report.pdf"
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

# ================= DELETE BUTTON =================

delete_btn = tk.Button(
    button_frame,
    text="Delete File",
    font=("Segoe UI", 12, "bold"),
    bg="#dc2626",
    fg="white",
    padx=35,
    pady=12,
    borderwidth=0,
    cursor="hand2",
    command=delete_file
)

delete_btn.grid(
    row=0,
    column=2,
    padx=15
)

# ================= EXPORT REPORT BUTTON =================

pdf_btn = tk.Button(
    button_frame,
    text="Export Report",
    font=("Segoe UI", 12, "bold"),
    bg="#2563eb",
    fg="white",
    padx=35,
    pady=12,
    borderwidth=0,
    cursor="hand2",
    command=export_pdf
)

pdf_btn.grid(
    row=0,
    column=3,
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

# ================= LIFT WIDGETS =================

header.lift()

button_frame.lift()

search_frame.lift()

status_label.lift()

count_label.lift()

table_container.lift()

footer.lift()

animate_particles()