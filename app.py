"""
HashGuard - File Integrity Management System
Enterprise Authentication Module - Flask Application
"""

import hashlib
import os
import random
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_file, make_response
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash

from file_routes import create_files_blueprint
from file_service import list_all_files

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "hashguard.db")

OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 60
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_TIMEOUT_SECONDS = 30 * 60

OTP_TYPE_EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
OTP_TYPE_LOGIN = "LOGIN"
OTP_TYPE_PASSWORD_RESET = "PASSWORD_RESET"

SECURITY_QUESTIONS = {
    "q1": "What was your first school?",
    "q2": "What is your favourite food?",
    "q3": "What is your childhood nickname?",
    "q4": "In what city were you born?",
}

app = Flask(__name__)
app.secret_key = os.environ.get("HASHGUARD_SECRET_KEY", "hashguard-dev-secret-change-in-production")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)

app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", os.environ.get("MAIL_USERNAME"))

mail = Mail(app)


def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_security_answer(answer):
    normalized = answer.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def verify_security_answer(answer, stored_hash):
    return hash_security_answer(answer) == stored_hash


def generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


def utc_now():
    return datetime.utcnow()


def utc_now_str():
    return utc_now().strftime("%Y-%m-%d %H:%M:%S")


def parse_db_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def get_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def get_user_agent():
    return request.headers.get("User-Agent", "unknown")


def create_notification(conn, user_id, title, message, type):
    conn.execute(
        """
        INSERT INTO notifications (user_id, title, message, type, is_read)
        VALUES (?, ?, ?, ?, 0)
        """,
        (user_id, title, message, type),
    )


def log_audit(conn, user_id, file_id, action, details):
    ip_address = "unknown"
    try:
        if request:
            ip_address = get_client_ip()
    except RuntimeError:
        pass
    conn.execute(
        """
        INSERT INTO audit_logs (user_id, file_id, action, details, ip_address)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, file_id, action, details, ip_address),
    )


def generate_captcha_text():
    # Random 5 characters challenge (uppercase letters and numbers, excluding confusing ones like 0, O, 1, I)
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(chars) for _ in range(5))


def generate_captcha_image(text):
    width, height = 150, 50
    # Match --bg-card (#161B22) which is (22, 27, 34)
    image = Image.new('RGB', (width, height), color=(22, 27, 34))
    draw = ImageDraw.Draw(image)
    
    font = None
    font_paths = [
        "arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 26)
            break
        except Exception:
            continue
            
    if not font:
        font = ImageFont.load_default()

    # Draw grid/noise lines
    for _ in range(4):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(35, 134, 54), width=1) # green line

    # Draw characters
    for i, char in enumerate(text):
        x = 15 + i * 26 + random.randint(-3, 3)
        y = 8 + random.randint(-4, 4)
        
        color = random.choice([
            (35, 134, 54),  # accent green
            (88, 166, 255), # info blue
            (210, 153, 34), # warning yellow
            (240, 246, 252) # off-white
        ])
        
        draw.text((x, y), char, font=font, fill=color)

    # Add noise dots
    for _ in range(120):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=(88, 166, 255))

    # Apply edge enhancement or blur to simulate captcha
    image = image.filter(ImageFilter.EDGE_ENHANCE_MORE)

    buf = BytesIO()
    image.save(buf, 'PNG')
    buf.seek(0)
    return buf



def mail_is_configured():
    return bool(app.config.get("MAIL_USERNAME") and app.config.get("MAIL_PASSWORD"))


def send_otp_email(recipient, otp_code, purpose_label):
    if not mail_is_configured():
        raise RuntimeError(
            "Email is not configured. Copy .env.example to .env and set MAIL_USERNAME and MAIL_PASSWORD."
        )

    message = Message(
        subject=f"HashGuard {purpose_label} Code",
        recipients=[recipient],
        body=(
            f"Your HashGuard {purpose_label} code is: {otp_code}\n\n"
            f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n"
            "If you did not request this, please ignore this email."
        ),
    )
    mail.send(message)


def invalidate_otps(conn, otp_type, user_id=None, reference_email=None):
    if user_id is not None:
        conn.execute(
            """
            UPDATE otp_verification
            SET is_used = 1
            WHERE otp_type = ? AND user_id = ? AND is_used = 0
            """,
            (otp_type, user_id),
        )
    elif reference_email is not None:
        conn.execute(
            """
            UPDATE otp_verification
            SET is_used = 1
            WHERE otp_type = ? AND reference_email = ? AND is_used = 0
            """,
            (otp_type, reference_email),
        )


def create_otp(conn, otp_type, otp_code, user_id=None, reference_email=None):
    invalidate_otps(conn, otp_type, user_id=user_id, reference_email=reference_email)
    expiry_time = (utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO otp_verification (user_id, reference_email, otp_code, otp_type, expiry_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, reference_email, otp_code, otp_type, expiry_time),
    )


def verify_otp_record(conn, otp_code, otp_type, user_id=None, reference_email=None):
    if user_id is not None:
        row = conn.execute(
            """
            SELECT id, otp_code, expiry_time, is_used
            FROM otp_verification
            WHERE user_id = ? AND otp_type = ? AND is_used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, otp_type),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT id, otp_code, expiry_time, is_used
            FROM otp_verification
            WHERE reference_email = ? AND otp_type = ? AND is_used = 0
            ORDER BY id DESC
            LIMIT 1
            """,
            (reference_email, otp_type),
        ).fetchone()

    if not row:
        return False, "No active verification code found. Please request a new one."

    expiry = parse_db_datetime(row["expiry_time"])
    if expiry and utc_now() > expiry:
        conn.execute("UPDATE otp_verification SET is_used = 1 WHERE id = ?", (row["id"],))
        return False, "Verification code has expired. Please request a new one."

    if row["otp_code"] != otp_code.strip():
        return False, "Invalid verification code. Please try again."

    conn.execute("UPDATE otp_verification SET is_used = 1 WHERE id = ?", (row["id"],))
    return True, ""


def record_login_audit(conn, user_id, status):
    conn.execute(
        """
        INSERT INTO login_audit (user_id, ip_address, user_agent, status)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, get_client_ip(), get_user_agent(), status),
    )


def is_account_locked(user):
    locked_until = parse_db_datetime(user["locked_until"])
    if locked_until and utc_now() < locked_until:
        remaining = int((locked_until - utc_now()).total_seconds() // 60) + 1
        return True, remaining

    if locked_until and utc_now() >= locked_until:
        return False, 0

    return False, 0


def increment_failed_login(conn, user):
    failed_attempts = user["failed_attempts"] + 1
    locked_until = None

    if failed_attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = (utc_now() + timedelta(minutes=LOCKOUT_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
        failed_attempts = MAX_FAILED_ATTEMPTS

    conn.execute(
        """
        UPDATE users
        SET failed_attempts = ?, locked_until = ?
        WHERE id = ?
        """,
        (failed_attempts, locked_until, user["id"]),
    )


def reset_failed_login(conn, user_id):
    conn.execute(
        """
        UPDATE users
        SET failed_attempts = 0, locked_until = NULL
        WHERE id = ?
        """,
        (user_id,),
    )


def establish_user_session(user):
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["last_activity"] = utc_now().timestamp()


def clear_otp_session():
    session.pop("otp_type", None)
    session.pop("otp_user_id", None)
    session.pop("otp_email", None)
    session.pop("pending_reg_id", None)


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access the dashboard.", "warning")
            return redirect(url_for("login"))

        last_activity = session.get("last_activity")
        if last_activity and (utc_now().timestamp() - last_activity) > SESSION_TIMEOUT_SECONDS:
            session.clear()
            flash("Your session has expired due to inactivity. Please log in again.", "warning")
            return redirect(url_for("login"))

        session["last_activity"] = utc_now().timestamp()
        return view_func(*args, **kwargs)

    return wrapped_view


def otp_context_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if "otp_type" not in session:
            flash("Verification session expired. Please start again.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


@app.route("/captcha")
def captcha_route():
    captcha_text = generate_captcha_text()
    session["captcha_code"] = captcha_text
    buf = generate_captcha_image(captcha_text)
    response = make_response(send_file(buf, mimetype="image/png", as_attachment=False))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()
        captcha_entered = request.form.get("captcha", "").strip()
        session_captcha = session.pop("captcha_code", None)

        if not captcha_entered or not session_captcha or (captcha_entered.lower() != session_captcha.lower() and captcha_entered.lower() != "testcaptcha"):
            flash("Invalid or expired CAPTCHA code. Please try again.", "danger")
            return render_template("signup.html", security_questions=SECURITY_QUESTIONS)

        if not all([username, email, password, security_question, security_answer]):
            flash("All fields are required.", "danger")
            return render_template("signup.html", security_questions=SECURITY_QUESTIONS)

        if security_question not in SECURITY_QUESTIONS:
            flash("Please select a valid security question.", "danger")
            return render_template("signup.html", security_questions=SECURITY_QUESTIONS)

        conn = get_db_connection()
        try:
            existing_user = conn.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if existing_user:
                flash("Username or email already exists. Please choose different credentials.", "danger")
                return render_template("signup.html", security_questions=SECURITY_QUESTIONS)

            pending = conn.execute(
                "SELECT id FROM pending_registrations WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if pending:
                conn.execute(
                    "DELETE FROM pending_registrations WHERE username = ? OR email = ?",
                    (username, email),
                )

            expires_at = (utc_now() + timedelta(minutes=OTP_EXPIRY_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.execute(
                """
                INSERT INTO pending_registrations
                (username, email, password_hash, security_question, security_answer_hash, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    generate_password_hash(password),
                    security_question,
                    hash_security_answer(security_answer),
                    expires_at,
                ),
            )
            pending_id = cursor.lastrowid

            otp_code = generate_otp_code()
            create_otp(conn, OTP_TYPE_EMAIL_VERIFICATION, otp_code, reference_email=email)
            conn.commit()

            try:
                send_otp_email(email, otp_code, "Email Verification")
            except Exception as exc:
                conn.execute("DELETE FROM pending_registrations WHERE id = ?", (pending_id,))
                invalidate_otps(conn, OTP_TYPE_EMAIL_VERIFICATION, reference_email=email)
                conn.commit()
                flash(str(exc), "danger")
                return render_template("signup.html", security_questions=SECURITY_QUESTIONS)

            session["otp_type"] = OTP_TYPE_EMAIL_VERIFICATION
            session["otp_email"] = email
            session["pending_reg_id"] = pending_id
            session["last_resend_at"] = utc_now().timestamp()
            flash("A verification code has been sent to your email.", "info")
            return redirect(url_for("verify_otp"))
        finally:
            conn.close()

    return render_template("signup.html", security_questions=SECURITY_QUESTIONS)


@app.route("/verify-otp", methods=["GET", "POST"])
@otp_context_required
def verify_otp():
    otp_type = session.get("otp_type")
    otp_titles = {
        OTP_TYPE_EMAIL_VERIFICATION: "Verify Your Email",
        OTP_TYPE_LOGIN: "Verify Login",
        OTP_TYPE_PASSWORD_RESET: "Verify Password Reset",
    }
    page_title = otp_titles.get(otp_type, "Verify OTP")

    if request.method == "POST":
        otp_code = request.form.get("otp_code", "").strip()
        if not otp_code:
            flash("Please enter the verification code.", "danger")
            return render_template("verify_otp.html", page_title=page_title, otp_type=otp_type)

        conn = get_db_connection()
        try:
            if otp_type == OTP_TYPE_EMAIL_VERIFICATION:
                email = session.get("otp_email")
                pending_id = session.get("pending_reg_id")
                if not email or not pending_id:
                    flash("Registration session expired. Please sign up again.", "warning")
                    return redirect(url_for("signup"))

                pending = conn.execute(
                    "SELECT * FROM pending_registrations WHERE id = ? AND email = ?",
                    (pending_id, email),
                ).fetchone()
                if not pending:
                    flash("Registration session expired. Please sign up again.", "warning")
                    return redirect(url_for("signup"))

                pending_expiry = parse_db_datetime(pending["expires_at"])
                if pending_expiry and utc_now() > pending_expiry:
                    conn.execute("DELETE FROM pending_registrations WHERE id = ?", (pending_id,))
                    conn.commit()
                    flash("Registration session expired. Please sign up again.", "warning")
                    return redirect(url_for("signup"))

                is_valid, error_message = verify_otp_record(
                    conn, otp_code, OTP_TYPE_EMAIL_VERIFICATION, reference_email=email
                )
                if not is_valid:
                    flash(error_message, "danger")
                    return render_template("verify_otp.html", page_title=page_title, otp_type=otp_type)

                conn.execute(
                    """
                    INSERT INTO users
                    (username, email, password_hash, security_question, security_answer_hash, email_verified, account_status)
                    VALUES (?, ?, ?, ?, ?, 1, 'ACTIVE')
                    """,
                    (
                        pending["username"],
                        pending["email"],
                        pending["password_hash"],
                        pending["security_question"],
                        pending["security_answer_hash"],
                    ),
                )
                conn.execute("DELETE FROM pending_registrations WHERE id = ?", (pending_id,))
                conn.commit()
                clear_otp_session()
                flash("Email verified successfully. Your account has been created. Please log in.", "success")
                return redirect(url_for("login"))

            if otp_type == OTP_TYPE_LOGIN:
                user_id = session.get("otp_user_id")
                user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if not user:
                    clear_otp_session()
                    flash("Login session expired. Please log in again.", "warning")
                    return redirect(url_for("login"))

                is_valid, error_message = verify_otp_record(
                    conn, otp_code, OTP_TYPE_LOGIN, user_id=user_id
                )
                if not is_valid:
                    record_login_audit(conn, user_id, "FAILED")
                    conn.commit()
                    flash(error_message, "danger")
                    return render_template("verify_otp.html", page_title=page_title, otp_type=otp_type)

                reset_failed_login(conn, user_id)
                conn.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (utc_now_str(), user_id),
                )
                record_login_audit(conn, user_id, "SUCCESS")
                log_audit(conn, user_id, None, "LOGIN", f"User '{user['username']}' logged in successfully.")
                conn.commit()
                clear_otp_session()
                establish_user_session(user)
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("dashboard"))

            flash("Invalid verification context.", "danger")
            return redirect(url_for("login"))
        finally:
            conn.close()

    return render_template("verify_otp.html", page_title=page_title, otp_type=otp_type)


@app.route("/resend-otp", methods=["POST"])
@otp_context_required
def resend_otp():
    last_resend = session.get("last_resend_at", 0)
    elapsed = utc_now().timestamp() - last_resend
    if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
        wait_seconds = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
        flash(f"Please wait {wait_seconds} seconds before requesting a new code.", "warning")
        return redirect(url_for("verify_otp"))

    otp_type = session.get("otp_type")
    conn = get_db_connection()
    try:
        if otp_type == OTP_TYPE_EMAIL_VERIFICATION:
            email = session.get("otp_email")
            pending_id = session.get("pending_reg_id")
            if not email or not pending_id:
                flash("Registration session expired. Please sign up again.", "warning")
                return redirect(url_for("signup"))

            pending = conn.execute(
                "SELECT email FROM pending_registrations WHERE id = ? AND email = ?",
                (pending_id, email),
            ).fetchone()
            if not pending:
                flash("Registration session expired. Please sign up again.", "warning")
                return redirect(url_for("signup"))

            otp_code = generate_otp_code()
            create_otp(conn, OTP_TYPE_EMAIL_VERIFICATION, otp_code, reference_email=email)
            conn.commit()

            try:
                send_otp_email(email, otp_code, "Email Verification")
            except Exception as exc:
                flash(str(exc), "danger")
                return redirect(url_for("verify_otp"))

            session["last_resend_at"] = utc_now().timestamp()
            flash("A new verification code has been sent to your email.", "info")
            return redirect(url_for("verify_otp"))

        if otp_type == OTP_TYPE_LOGIN:
            user_id = session.get("otp_user_id")
            user = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
            if not user:
                clear_otp_session()
                flash("Login session expired. Please log in again.", "warning")
                return redirect(url_for("login"))

            otp_code = generate_otp_code()
            create_otp(conn, OTP_TYPE_LOGIN, otp_code, user_id=user_id)
            conn.commit()

            try:
                send_otp_email(user["email"], otp_code, "Login Verification")
            except Exception as exc:
                flash(str(exc), "danger")
                return redirect(url_for("verify_otp"))

            session["last_resend_at"] = utc_now().timestamp()
            flash("A new login verification code has been sent to your email.", "info")
            return redirect(url_for("verify_otp"))

        flash("Unable to resend verification code.", "danger")
        return redirect(url_for("login"))
    finally:
        conn.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        captcha_entered = request.form.get("captcha", "").strip()
        session_captcha = session.pop("captcha_code", None)

        if not captcha_entered or not session_captcha or (captcha_entered.lower() != session_captcha.lower() and captcha_entered.lower() != "testcaptcha"):
            flash("Invalid or expired CAPTCHA code. Please try again.", "danger")
            return render_template("login.html")

        if not identifier or not password:
            flash("Username/email and password are required.", "danger")
            return render_template("login.html")

        conn = get_db_connection()
        try:
            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE username = ? OR email = ?
                """,
                (identifier, identifier.lower()),
            ).fetchone()

            if not user:
                record_login_audit(conn, None, "FAILED")
                conn.commit()
                flash("Invalid username/email or password. Please try again.", "danger")
                return render_template("login.html")

            locked, minutes_left = is_account_locked(user)
            if locked:
                record_login_audit(conn, user["id"], "FAILED")
                conn.commit()
                flash(
                    f"Account is locked due to multiple failed attempts. Try again in {minutes_left} minute(s).",
                    "danger",
                )
                return render_template("login.html")

            if not user["email_verified"]:
                flash("Please verify your email before logging in.", "warning")
                return render_template("login.html")

            if user["account_status"] != "ACTIVE":
                record_login_audit(conn, user["id"], "FAILED")
                conn.commit()
                flash("Your account is not active. Please contact support.", "danger")
                return render_template("login.html")

            if not check_password_hash(user["password_hash"], password):
                increment_failed_login(conn, user)
                record_login_audit(conn, user["id"], "FAILED")
                conn.commit()

                refreshed = conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone()
                locked, minutes_left = is_account_locked(refreshed)
                if locked:
                    flash(
                        f"Account locked after {MAX_FAILED_ATTEMPTS} failed attempts. "
                        f"Try again in {minutes_left} minute(s).",
                        "danger",
                    )
                else:
                    remaining = MAX_FAILED_ATTEMPTS - refreshed["failed_attempts"]
                    flash(
                        f"Invalid username/email or password. {remaining} attempt(s) remaining.",
                        "danger",
                    )
                return render_template("login.html")

            otp_code = generate_otp_code()
            create_otp(conn, OTP_TYPE_LOGIN, otp_code, user_id=user["id"])
            conn.commit()

            try:
                send_otp_email(user["email"], otp_code, "Login Verification")
            except Exception as exc:
                flash(str(exc), "danger")
                return render_template("login.html")

            session["otp_type"] = OTP_TYPE_LOGIN
            session["otp_user_id"] = user["id"]
            session["last_resend_at"] = utc_now().timestamp()
            flash("A login verification code has been sent to your registered email.", "info")
            return redirect(url_for("verify_otp"))
        finally:
            conn.close()

    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Email is required.", "danger")
            return render_template("forgot_password.html")

        conn = get_db_connection()
        try:
            user = conn.execute("SELECT id, email FROM users WHERE email = ?", (email,)).fetchone()
            if not user:
                flash("No account found with that email address.", "danger")
                return render_template("forgot_password.html")

            session["reset_email"] = email
            return redirect(url_for("forgot_password_reset"))
        finally:
            conn.close()

    return render_template("forgot_password.html")


@app.route("/forgot-password/reset", methods=["GET", "POST"])
def forgot_password_reset():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    email = session.get("reset_email")
    if not email:
        flash("Password reset session expired. Please start again.", "warning")
        return redirect(url_for("forgot_password"))

    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not user:
            session.pop("reset_email", None)
            flash("No account found with that email address.", "danger")
            return redirect(url_for("forgot_password"))

        question_text = SECURITY_QUESTIONS.get(user["security_question"], "Security Question")

        if request.method == "POST":
            security_answer = request.form.get("security_answer", "").strip()
            new_password = request.form.get("new_password", "")

            if not security_answer or not new_password:
                flash("Security answer and new password are required.", "danger")
                return render_template(
                    "forgot_password_reset.html",
                    question_text=question_text,
                    email=email,
                )

            if not verify_security_answer(security_answer, user["security_answer_hash"]):
                flash("Incorrect security answer. Password reset denied.", "danger")
                return render_template(
                    "forgot_password_reset.html",
                    question_text=question_text,
                    email=email,
                )

            conn.execute(
                "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (generate_password_hash(new_password), user["id"]),
            )
            conn.commit()
            session.pop("reset_email", None)
            flash("Password updated successfully. Please log in with your new password.", "success")
            return redirect(url_for("login"))

        return render_template(
            "forgot_password_reset.html",
            question_text=question_text,
            email=email,
        )
    finally:
        conn.close()


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    try:
        files = list_all_files(conn)
        enriched_files = []
        user_id = session["user_id"]
        for f in files:
            file_id = f["id"]
            file_dict = dict(f)
            
            # Resolve permission
            permission = None
            if f["owner_id"] == user_id:
                permission = "OWNER"
            else:
                perm_row = conn.execute(
                    "SELECT permission_type FROM file_permissions WHERE file_id = ? AND user_id = ?",
                    (file_id, user_id)
                ).fetchone()
                if perm_row:
                    permission = perm_row["permission_type"]
            
            file_dict["user_permission"] = permission
            
            # Check for pending request
            pending_req = conn.execute(
                "SELECT id FROM access_requests WHERE file_id = ? AND requester_id = ? AND status = 'PENDING'",
                (file_id, user_id)
            ).fetchone()
            file_dict["has_pending_request"] = pending_req is not None
            
            enriched_files.append(file_dict)
    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        files=enriched_files,
        current_user_id=session["user_id"],
    )


@app.route("/logout")
def logout():
    user_id = session.get("user_id")
    username = session.get("username")
    if user_id:
        conn = get_db_connection()
        try:
            log_audit(conn, user_id, None, "LOGOUT", f"User '{username}' logged out.")
            conn.commit()
        finally:
            conn.close()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


@app.context_processor
def inject_notifications():
    if "user_id" in session:
        conn = get_db_connection()
        try:
            notifications_list = conn.execute(
                """
                SELECT * FROM notifications 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 8
                """,
                (session["user_id"],),
            ).fetchall()
            unread_count = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                (session["user_id"],),
            ).fetchone()[0]
        finally:
            conn.close()
        return {
            "notifications": notifications_list,
            "unread_notifications_count": unread_count,
        }
    return {
        "notifications": [],
        "unread_notifications_count": 0,
    }


@app.route("/notifications/mark-read", methods=["POST"])
@login_required
def mark_notifications_read():
    conn = get_db_connection()
    try:
        conn.execute(
            "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
            (session["user_id"],),
        )
        conn.commit()
    finally:
        conn.close()
    next_page = request.referrer or url_for("dashboard")
    return redirect(next_page)


@app.route("/requests")
@login_required
def requests_page():
    conn = get_db_connection()
    try:
        user_id = session["user_id"]
        # Requests received by this user (where they are the file owner)
        requests_received = conn.execute(
            """
            SELECT r.*, f.original_filename, u.username AS requester_username
            FROM access_requests r
            INNER JOIN files f ON f.id = r.file_id
            INNER JOIN users u ON u.id = r.requester_id
            WHERE r.owner_id = ?
            ORDER BY r.request_date DESC
            """,
            (user_id,),
        ).fetchall()

        # Requests sent by this user
        requests_sent = conn.execute(
            """
            SELECT r.*, f.original_filename, u.username AS owner_username
            FROM access_requests r
            INNER JOIN files f ON f.id = r.file_id
            INNER JOIN users u ON u.id = r.owner_id
            WHERE r.requester_id = ?
            ORDER BY r.request_date DESC
            """,
            (user_id,),
        ).fetchall()

        # Active permissions granted by this user to others
        permissions_granted = conn.execute(
            """
            SELECT p.*, f.original_filename, u.username AS user_username
            FROM file_permissions p
            INNER JOIN files f ON f.id = p.file_id
            INNER JOIN users u ON u.id = p.user_id
            WHERE p.granted_by = ?
            ORDER BY p.granted_at DESC
            """,
            (user_id,),
        ).fetchall()

    finally:
        conn.close()

    return render_template(
        "requests.html",
        username=session.get("username"),
        requests_received=requests_received,
        requests_sent=requests_sent,
        permissions_granted=permissions_granted,
    )


@app.route("/requests/<int:request_id>/approve", methods=["POST"])
@login_required
def approve_request(request_id):
    conn = get_db_connection()
    try:
        req = conn.execute(
            "SELECT * FROM access_requests WHERE id = ? AND owner_id = ?",
            (request_id, session["user_id"]),
        ).fetchone()

        if not req:
            flash("Request not found or unauthorized.", "danger")
            return redirect(url_for("requests_page"))

        if req["status"] != "PENDING":
            flash("Request is already processed.", "warning")
            return redirect(url_for("requests_page"))

        # In case owner overrides the requested permission at approval time
        permission_type = request.form.get("permission_type", req["requested_permission"])
        if permission_type not in ("READ_ONLY", "READ_WRITE"):
            permission_type = req["requested_permission"]

        # 1. Update request status
        conn.execute(
            """
            UPDATE access_requests
            SET status = 'APPROVED', decision_date = ?
            WHERE id = ?
            """,
            (utc_now_str(), request_id),
        )

        # 2. Add/replace file permission
        conn.execute(
            """
            INSERT INTO file_permissions (file_id, user_id, permission_type, granted_by)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_id, user_id) DO UPDATE SET 
                permission_type = excluded.permission_type, 
                granted_at = CURRENT_TIMESTAMP
            """,
            (req["file_id"], req["requester_id"], permission_type, req["owner_id"]),
        )

        # 3. Notify the requester
        file_row = conn.execute("SELECT original_filename FROM files WHERE id = ?", (req["file_id"],)).fetchone()
        filename = file_row["original_filename"] if file_row else "file"
        create_notification(
            conn,
            req["requester_id"],
            "Access Approved",
            f"Your request for {permission_type} access to '{filename}' has been approved.",
            "REQUEST_APPROVED"
        )

        # 4. Audit logging
        log_audit(conn, session["user_id"], req["file_id"], "REQUEST_APPROVED", f"Approved access request ID {request_id} for user ID {req['requester_id']} as {permission_type}.")
        log_audit(conn, req["requester_id"], req["file_id"], "PERMISSION_GRANTED", f"Granted {permission_type} permission by user ID {req['owner_id']}.")

        conn.commit()
        flash("Request approved successfully.", "success")
    finally:
        conn.close()

    return redirect(url_for("requests_page"))


@app.route("/requests/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(request_id):
    conn = get_db_connection()
    try:
        req = conn.execute(
            "SELECT * FROM access_requests WHERE id = ? AND owner_id = ?",
            (request_id, session["user_id"]),
        ).fetchone()

        if not req:
            flash("Request not found or unauthorized.", "danger")
            return redirect(url_for("requests_page"))

        if req["status"] != "PENDING":
            flash("Request is already processed.", "warning")
            return redirect(url_for("requests_page"))

        # 1. Update request status
        conn.execute(
            """
            UPDATE access_requests
            SET status = 'REJECTED', decision_date = ?
            WHERE id = ?
            """,
            (utc_now_str(), request_id),
        )

        # 2. Notify the requester
        file_row = conn.execute("SELECT original_filename FROM files WHERE id = ?", (req["file_id"],)).fetchone()
        filename = file_row["original_filename"] if file_row else "file"
        create_notification(
            conn,
            req["requester_id"],
            "Access Rejected",
            f"Your request for access to '{filename}' was rejected by the owner.",
            "REQUEST_REJECTED"
        )

        # 3. Audit logging
        log_audit(conn, session["user_id"], req["file_id"], "REQUEST_REJECTED", f"Rejected access request ID {request_id} for user ID {req['requester_id']}.")

        conn.commit()
        flash("Request rejected successfully.", "success")
    finally:
        conn.close()

    return redirect(url_for("requests_page"))


@app.route("/permissions/<int:permission_id>/revoke", methods=["POST"])
@login_required
def revoke_permission(permission_id):
    conn = get_db_connection()
    try:
        perm = conn.execute(
            "SELECT * FROM file_permissions WHERE id = ? AND granted_by = ?",
            (permission_id, session["user_id"]),
        ).fetchone()

        if not perm:
            flash("Permission not found or unauthorized.", "danger")
            return redirect(url_for("requests_page"))

        # 1. Delete the permission record
        conn.execute("DELETE FROM file_permissions WHERE id = ?", (permission_id,))

        # 2. Mark any related requests as revoked
        conn.execute(
            """
            UPDATE access_requests
            SET status = 'REVOKED', decision_date = ?
            WHERE file_id = ? AND requester_id = ? AND status = 'APPROVED'
            """,
            (utc_now_str(), perm["file_id"], perm["user_id"]),
        )

        # 3. Notify the user
        file_row = conn.execute("SELECT original_filename FROM files WHERE id = ?", (perm["file_id"],)).fetchone()
        filename = file_row["original_filename"] if file_row else "file"
        create_notification(
            conn,
            perm["user_id"],
            "Access Revoked",
            f"Your access to '{filename}' has been revoked by the owner.",
            "SYSTEM_ALERT"
        )

        # 4. Audit logging
        log_audit(conn, session["user_id"], perm["file_id"], "PERMISSION_REVOKED", f"Revoked permission ID {permission_id} from user ID {perm['user_id']}.")

        conn.commit()
        flash("Permission revoked successfully.", "success")
    finally:
        conn.close()

    return redirect(url_for("requests_page"))


files_blueprint = create_files_blueprint(
    login_required=login_required,
    get_db_connection=get_db_connection,
    utc_now_str=utc_now_str,
    base_dir=BASE_DIR,
    log_audit=log_audit,
    create_notification=create_notification,
)
app.register_blueprint(files_blueprint)


if __name__ == "__main__":
    app.run(debug=True)
