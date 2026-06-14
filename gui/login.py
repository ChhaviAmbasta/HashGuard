
import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog
import hashlib
import sys
import os
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)
from PIL import Image, ImageTk
import random
import smtplib
import time

from email.mime.text import MIMEText

# Allow dashboard import
sys.path.append(os.path.dirname(__file__))

# ================= DATABASE =================
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    username TEXT UNIQUE,

    email TEXT UNIQUE,

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

# ================= CAPTCHA =================
captcha_value = str(random.randint(1000, 9999))

# ================= CAPTCHA UI =================

captcha_label = tk.Label(
    frame,
    text=f"CAPTCHA: {captcha_value}",
    font=("Segoe UI", 11, "bold"),
    fg="yellow",
    bg="#111c44"
)
captcha_label.pack(anchor="w")

captcha_entry = tk.Entry(
    frame,
    font=("Segoe UI", 12),
    width=28
)

captcha_entry.pack(pady=(5, 20), ipady=7)

# ================= HASH FUNCTION =================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ================= OTP VARIABLES =================

current_otp = None
current_email = None
otp_expiry = None



# ================= OTP GENERATION =================

def generate_otp():
    return str(random.randint(100000, 999999))

# ================= SEND OTP =================

def send_otp(email):

    global current_otp
    global current_email
    global otp_expiry

    current_otp = generate_otp()
    current_email = email

    otp_expiry = time.time() + 300

    sender_email = os.getenv("HASHGUARD_EMAIL")
    sender_password = os.getenv("HASHGUARD_APP_PASSWORD")
    print("HASHGUARD_EMAIL =", sender_email)
    print("HASHGUARD_APP_PASSWORD =", sender_password)

    message = MIMEText(
        f"""
HashGuard Security Verification

Your OTP is:

{current_otp}

This OTP is valid for 5 minutes.
"""
    )

    message["Subject"] = "HashGuard Login OTP"
    message["From"] = sender_email
    message["To"] = email

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.sendmail(
            sender_email,
            email,
            message.as_string()
        )

        server.quit()

        return True

    except Exception as e:

        print("OTP Error:", e)

        return False
# ================= OTP WINDOW =================

def verify_otp_window(email):

    otp_window = tk.Toplevel(root)

    otp_window.title("OTP Verification")

    otp_window.geometry("350x250")

    otp_window.configure(bg="#111c44")

    tk.Label(
        otp_window,
        text="Enter OTP",
        font=("Segoe UI", 18, "bold"),
        bg="#111c44",
        fg="white"
    ).pack(pady=20)

    otp_entry = tk.Entry(
        otp_window,
        font=("Segoe UI", 14),
        justify="center"
    )

    otp_entry.pack(pady=10)

    def verify():

        otp = otp_entry.get()

        if time.time() > otp_expiry:

            messagebox.showerror(
                "Expired",
                "OTP expired"
            )

            return

        if otp == current_otp:

            messagebox.showinfo(
                "Success",
                "Login Successful"
            )

            otp_window.destroy()
            root.destroy()

            import dashboard

            dashboard.open_dashboard(email)

        else:

            messagebox.showerror(
                "Error",
                "Invalid OTP"
            )

    tk.Button(
        otp_window,
        text="Verify",
        command=verify,
        bg="#4f46e5",
        fg="white",
        width=15
    ).pack(pady=20)

# ================= RESET PASSWORD WINDOW =================

def reset_password_window(email):

    reset_window = tk.Toplevel(root)

    reset_window.title("Reset Password")

    reset_window.geometry("350x250")

    reset_window.configure(bg="#111c44")

    tk.Label(
        reset_window,
        text="New Password",
        bg="#111c44",
        fg="white"
    ).pack(pady=10)

    new_pass_entry = tk.Entry(
        reset_window,
        show="*"
    )

    new_pass_entry.pack(pady=5)

    tk.Label(
        reset_window,
        text="Confirm Password",
        bg="#111c44",
        fg="white"
    ).pack(pady=10)

    confirm_pass_entry = tk.Entry(
        reset_window,
        show="*"
    )

    confirm_pass_entry.pack(pady=5)

    def save_password():

        new_password = new_pass_entry.get()

        confirm_password = confirm_pass_entry.get()

        if new_password == "" or confirm_password == "":

            messagebox.showerror(
                "Error",
                "Please fill all fields"
            )

            return

        if new_password != confirm_password:

            messagebox.showerror(
                "Error",
                "Passwords do not match"
            )

            return

        hashed_password = hash_password(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password=?
            WHERE email=?
            """,
            (
                hashed_password,
                email
            )
        )

        conn.commit()

        messagebox.showinfo(
            "Success",
            "Password Updated Successfully"
        )

        reset_window.destroy()

    tk.Button(
        reset_window,
        text="Save Password",
        command=save_password,
        bg="#16a34a",
        fg="white"
    ).pack(pady=20)

# ================= LOGIN FUNCTION =================
def login():

    username = username_entry.get()
    password = password_entry.get()
    captcha = captcha_entry.get()

    if captcha != captcha_value:
        
        messagebox.showerror(
            "Error",
            "Invalid CAPTCHA"
        )

        return

   

    if username == "" or password == "":
        messagebox.showerror(
            "Error",
            "Please fill all fields"
        )
        return

    hashed_password = hash_password(password)

    cursor.execute(
        """
        SELECT email
        FROM users
        WHERE (username=? OR email=?)
        AND password=?
        """,
        (
            username,
            username,
            hashed_password
        )
    )

    user = cursor.fetchone()

    if user:
        email = user[0]
        
        if send_otp(email):
            
            messagebox.showinfo(
                
                "OTP Sent",
                f"OTP sent to {email}"
            )

            verify_otp_window(email)

        else:
            
            messagebox.showerror(
                "Error",
                "Could not send OTP"
           )

    else:
        messagebox.showerror(
            "Access Denied",
            "Invalid Username or Password"
    )

def forgot_password():

    email = simpledialog.askstring(
        "Forgot Password",
        "Enter your registered email:"
    )

    if not email:
        return

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    )

    user = cursor.fetchone()

    if not user:

        messagebox.showerror(
            "Error",
            "Email not found"
        )

        return

    if send_otp(email):

        messagebox.showinfo(
            "OTP Sent",
            "Password reset OTP sent to your email."
        )

        otp_window = tk.Toplevel(root)

        otp_window.title("OTP Verification")

        otp_window.geometry("350x250")

        otp_window.configure(bg="#111c44")

        tk.Label(
            otp_window,
            text="Enter OTP",
            font=("Segoe UI", 16, "bold"),
            bg="#111c44",
            fg="white"
        ).pack(pady=20)

        otp_entry = tk.Entry(
            otp_window,
            font=("Segoe UI", 14)
        )

        otp_entry.pack(pady=10)

        def verify_reset_otp():

            entered_otp = otp_entry.get()

            if time.time() > otp_expiry:

                messagebox.showerror(
                    "Expired",
                    "OTP expired"
                )

                return

            if entered_otp == current_otp:

                otp_window.destroy()

                reset_password_window(email)

            else:

                messagebox.showerror(
                    "Error",
                    "Invalid OTP"
                )

        tk.Button(
            otp_window,
            text="Verify OTP",
            command=verify_reset_otp,
            bg="#4f46e5",
            fg="white"
        ).pack(pady=20)

    else:

        messagebox.showerror(
            "Error",
            "Could not send OTP."
        )
        
# ================= CREATE ACCOUNT FUNCTION =================
def create_account():

    register_window = tk.Toplevel(root)
    register_window.title("Create Account")
    register_window.geometry("420x600")
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

    # ===== EMAIL =====
    email_label = tk.Label(
        register_window,
        text="Email",
        font=("Segoe UI", 11),
        fg="white",
        bg="#111c44"
        
        )
    email_label.pack(anchor="w", padx=40)
    
    email_entry = tk.Entry(
        register_window,
        font=("Segoe UI", 12),
        width=28
        )
    
    email_entry.pack(pady=(5, 20), ipady=7)


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
        email = email_entry.get()
        password = pass_entry.get()
        confirm = confirm_entry.get()

        if username == "" or email == "" or password == "" or confirm == "":
            messagebox.showerror(
                "Error",
                "Please fill all fields"
            )
            return

        if "@" not in email or "." not in email:
            messagebox.showerror(
                "Error",
                "Please enter a valid email address"
            )
            return
            

        if password != confirm:
            messagebox.showerror(
                "Error",
                "Passwords do not match"
            )
            return

        hashed_password = hash_password(password)
        if not send_otp(email):
            messagebox.showerror(
                "Error",
                "Could not verify email."
            )

            return

        messagebox.showinfo(
            "Verification",
            "OTP sent to your email. Verify before registration."
        )

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed_password)
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
    register_btn.pack(pady=20)

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
forgot_btn = tk.Button(
    frame,
    text="Forgot Password?",
    font=("Segoe UI", 10),
    bg="#111c44",
    fg="#00ffff",
    borderwidth=0,
    cursor="hand2",
    command=forgot_password
)

forgot_btn.pack()

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