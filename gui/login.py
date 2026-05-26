import tkinter as tk
from tkinter import messagebox
import sqlite3
import hashlib
import sys
import os
from PIL import Image, ImageTk
import random

# Allow dashboard import
sys.path.append(os.path.dirname(__file__))

# ================= DATABASE =================
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

conn.commit()
# ================= MAIN WINDOW =================
root = tk.Tk()

root.title("HashGuard Login")

root.geometry("900x700")

root.minsize(700, 650)

root.configure(bg="#0b1437")

# ================= ANIMATED BACKGROUND =================

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

for i in range(120):

    x = random.randint(0, root.winfo_screenwidth())
    y = random.randint(0, root.winfo_screenheight())

    size = random.randint(1, 3)

    particle = canvas.create_oval(
        x,
        y,
        x + size,
        y + size,
        fill="#00ffff",
        outline=""
    )

    dx = random.choice([-1, 1]) * random.uniform(0.3, 1)
    dy = random.choice([-1, 1]) * random.uniform(0.3, 1)

    particles.append([particle, dx, dy])

def animate_particles():

    for p in particles:

        particle = p[0]
        dx = p[1]
        dy = p[2]

        canvas.move(particle, dx, dy)

        coords = canvas.coords(particle)

        if coords[0] <= 0 or coords[2] >= root.winfo_width():
            p[1] = -dx

        if coords[1] <= 0 or coords[3] >= root.winfo_height():
            p[2] = -dy

    root.after(30, animate_particles)

animate_particles()

# ================= LOGO =================

logo_img = Image.open("assets/HashGuard_logo.png")

logo_img = logo_img.resize((85, 95))

logo_photo = ImageTk.PhotoImage(logo_img)

logo_label = tk.Label(
    root,
    image=logo_photo,
    bg="#0b1437"
)

logo_label.pack(pady=(20, 5))
logo_label.lift()

# ================= TITLE =================
title = tk.Label(
    root,
    text="HashGuard",
    font=("Segoe UI", 32, "bold"),
    fg="white",
    bg="#0b1437"
)
title.pack(pady=(5, 5))
title.lift()

subtitle = tk.Label(
    root,
    text="Secure File Integrity System",
    font=("Segoe UI", 13),
    fg="#cbd5e1",
    bg="#0b1437"
)
subtitle.pack(pady=(0, 25))
subtitle.lift()

# ================= LOGIN FRAME =================
frame = tk.Frame(
    root,
    bg="#111c44",
    padx=40,
    pady=40
)
frame.place(
    relx=0.5,
    rely=0.63,
    anchor="center"
)
frame.lift()

login_label = tk.Label(
    frame,
    text="Login",
    font=("Segoe UI", 26, "bold"),
    fg="white",
    bg="#111c44"
)
login_label.pack(pady=(0, 30))

# ================= USERNAME =================
username_label = tk.Label(
    frame,
    text="Username",
    font=("Segoe UI", 11),
    fg="white",
    bg="#111c44"
)
username_label.pack(anchor="w")

username_entry = tk.Entry(
    frame,
    font=("Segoe UI", 12),
    width=28
)
username_entry.pack(pady=(5, 20), ipady=7)

# ================= PASSWORD =================
password_label = tk.Label(
    frame,
    text="Password",
    font=("Segoe UI", 11),
    fg="white",
    bg="#111c44"
)
password_label.pack(anchor="w")

password_entry = tk.Entry(
    frame,
    font=("Segoe UI", 12),
    width=28,
    show="*"
)
password_entry.pack(pady=(5, 25), ipady=7)

# ================= HASH FUNCTION =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= LOGIN FUNCTION =================
def login():

    username = username_entry.get()
    password = password_entry.get()

    if username == "" or password == "":
        messagebox.showerror(
            "Error",
            "Please fill all fields"
        )
        return

    hashed_password = hash_password(password)

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, hashed_password)
    )

    user = cursor.fetchone()

    if user:

        messagebox.showinfo(
            "Success",
            f"Welcome {username}"
        )

        root.destroy()

        import dashboard

        dashboard.open_dashboard(username)

    else:
        messagebox.showerror(
            "Access Denied",
            "Invalid Username or Password"
        )

# ================= CREATE ACCOUNT FUNCTION =================
def create_account():

    register_window = tk.Toplevel(root)
    register_window.title("Create Account")
    register_window.geometry("420x500")
    register_window.configure(bg="#111c44")

    # ===== TITLE =====
    title = tk.Label(
        register_window,
        text="Create Account",
        font=("Segoe UI", 24, "bold"),
        fg="white",
        bg="#111c44"
    )
    title.pack(pady=30)

    # ===== USERNAME =====
    user_label = tk.Label(
        register_window,
        text="Username",
        font=("Segoe UI", 11),
        fg="white",
        bg="#111c44"
    )
    user_label.pack(anchor="w", padx=40)

    user_entry = tk.Entry(
        register_window,
        font=("Segoe UI", 12),
        width=28
    )
    user_entry.pack(pady=(5, 20), ipady=7)

    # ===== PASSWORD =====
    pass_label = tk.Label(
        register_window,
        text="Password",
        font=("Segoe UI", 11),
        fg="white",
        bg="#111c44"
    )
    pass_label.pack(anchor="w", padx=40)

    pass_entry = tk.Entry(
        register_window,
        font=("Segoe UI", 12),
        width=28,
        show="*"
    )
    pass_entry.pack(pady=(5, 20), ipady=7)

    # ===== CONFIRM PASSWORD =====
    confirm_label = tk.Label(
        register_window,
        text="Confirm Password",
        font=("Segoe UI", 11),
        fg="white",
        bg="#111c44"
    )
    confirm_label.pack(anchor="w", padx=40)

    confirm_entry = tk.Entry(
        register_window,
        font=("Segoe UI", 12),
        width=28,
        show="*"
    )
    confirm_entry.pack(pady=(5, 30), ipady=7)

    # ===== REGISTER FUNCTION =====
    def register():

        username = user_entry.get()
        password = pass_entry.get()
        confirm = confirm_entry.get()

        if username == "" or password == "" or confirm == "":
            messagebox.showerror(
                "Error",
                "Please fill all fields"
            )
            return

        if password != confirm:
            messagebox.showerror(
                "Error",
                "Passwords do not match"
            )
            return

        hashed_password = hash_password(password)

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed_password)
            )

            conn.commit()

            messagebox.showinfo(
                "Success",
                "Account Created Successfully"
            )

            register_window.destroy()

        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Error",
                "Username already exists"
            )

    # ===== REGISTER BUTTON =====
    register_btn = tk.Button(
        register_window,
        text="Create Account",
        font=("Segoe UI", 12, "bold"),
        bg="#16a34a",
        fg="white",
        width=24,
        pady=10,
        borderwidth=0,
        command=register
    )
    register_btn.pack()

# ================= BUTTONS =================
login_btn = tk.Button(
    frame,
    text="Login",
    font=("Segoe UI", 12, "bold"),
    bg="#4f46e5",
    fg="white",
    width=28,
    height=2,
    borderwidth=0,
    cursor="hand2",
    command=login
)

login_btn.pack(pady=(15, 15))


create_btn = tk.Button(
    frame,
    text="Create Account",
    font=("Segoe UI", 12, "bold"),
    bg="#16a34a",
    fg="white",
    width=28,
    height=2,
    borderwidth=0,
    cursor="hand2",
    command=create_account
)

create_btn.pack(pady=(0, 10))

# ================= FOOTER =================
footer = tk.Label(
    root,
    text="© 2026 HashGuard | Secure File Integrity System",
    font=("Segoe UI", 10),
    fg="#94a3b8",
    bg="#0b1437"
)
footer.place(
    relx=0.5,
    rely=0.97,
    anchor="center"
)
footer.lift()

# ================= RUN =================
root.mainloop()