# HashGuard

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.x-green)
![SQLite](https://img.shields.io/badge/sqlite-3-lightgrey)
![Security](https://img.shields.io/badge/security-AES--256--GCM-red)

**HashGuard** is a secure, end-to-end encrypted file vault built with Flask. It provides audit-ready file storage with AES-256-GCM encryption at rest, SHA-256 integrity verification, granular access controls, and comprehensive activity monitoring.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Installation Instructions](#installation-instructions)
- [Configuration (.env Requirements)](#configuration-env-requirements)
- [Database Overview](#database-overview)
- [Security Features](#security-features)
- [File Structure](#file-structure)
- [Usage Guide](#usage-guide)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

## Project Overview

HashGuard is a secure file management platform that combines enterprise-style authentication with encrypted file storage. Each uploaded file is encrypted before it ever reaches the disk, hashed for tamper detection, and protected behind a permission-based access control system.

The application enforces strict authentication flows: CAPTCHA-protected registration and login, email-based OTP verification, security-question password recovery, and automatic account lockout after repeated failed attempts. Once authenticated, users can upload, download, verify, compare, and share files through an approval-based request system.

All critical actions are logged to a consolidated audit trail, enabling full forensics of who accessed what, when, and from where.

---

## Features

### Authentication & Authorization
- **CAPTCHA-protected signup and login** — server-side generated PNG captcha with noise and grid distortion
- **Email OTP verification** — 6-digit one-time password for registration, login, and password reset flows
- **Account lockout** — automatic 15-minute lockout after 5 failed login attempts
- **Security question recovery** — 4 pre-defined questions with SHA-256 hashed answers
- **Tiered file permissions** — `READ_ONLY` (download, verify, view) and `READ_WRITE` (download + replace content)
- **Access request workflow** — non-owners submit requests; owners approve or reject with customizable permission level
- **Permission revocation** — owners can revoke granted access at any time

### File Security
- **AES-256-GCM encryption at rest** — files are encrypted before disk write; key stored in environment variable
- **Dual SHA-256 hashing**:
  - `sha256_hash` — byte-for-byte hash of decrypted content for integrity checks
  - `content_hash` — normalized content hash for semantic duplicate detection (TXT, DOCX, PDF)
- **Randomized filenames** — stored as `secrets.token_hex(16)` with original extension
- **On-demand integrity verification** — decrypt, re-hash, and compare against stored hash on demand
- **Tamper detection** — modified files are flagged with `MODIFIED` status and trigger tamper-alert notifications
- **Soft delete** — files marked `is_deleted=1` preserving forensic trail

### Monitoring & Auditing
- **Consolidated audit log** — paginated, searchable system-wide events (login, logout, compare, permission changes)
- **File-specific audit trail** — per-file history of uploads, downloads, verifications, deletions, and modifications
- **Login audit** — IP address, user-agent, and success/failure status per attempt
- **Real-time notifications** — access requests, approvals, rejections, revocations, and tamper alerts
- **Searchable audit interface** — full-text search across timestamp, username, file name, action, and details

### File Management
- **Upload validation** — whitelist (`pdf, txt, docx, xlsx, pptx, png, jpg, jpeg`) and blacklist (`exe, bat, cmd, msi, sh, apk`)
- **Duplicate detection** — owner-level checks on both byte hash and normalized content hash
- **Global file repository** — browse all uploaded files with permission indicators
- **File comparison** — upload a local file and compare its content hash against a repository file
- **Content replacement** — `READ_WRITE` holders can replace file contents; owners are notified
- **Drag-and-drop upload UI** — client-side drag-and-drop with file type and size feedback

---

## Architecture Overview

HashGuard follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│                     Frontend                        │
│  Bootstrap 5.3.3 / Custom Cybersecurity Theme       │
│  /templates + /static/css + /static/js              │
├─────────────────────────────────────────────────────┤
│                  Flask Application                  │
│  app.py — routes, decorators, auth logic,           │
│  business workflows, notification system            │
├─────────────────────────────────────────────────────┤
│                 Service Layer                       │
│  file_service.py — upload, download, integrity,     │
│  permissions, audit, replacement logic              │
├─────────────────────────────────────────────────────┤
│                   Utilities                         │
│  utils/encryption.py — AES-256-GCM                  │
│  utils/file_hash.py — SHA-256 / content hashing     │
│  utils/file_validator.py — type & size validation   │
├─────────────────────────────────────────────────────┤
│                 Data Layer                          │
│  Raw SQLite3 via sqlite3.Row                        │
│  schema.sql — 7 tables, 11 indexes                  │
│  create_db.py / migrate_db.py                       │
└─────────────────────────────────────────────────────┘
```

### Key Design Decisions
- **Raw SQLite (no ORM)** — the application issues parameterized SQL directly for full control over queries and transactions
- **Blueprint isolation** — file operations are hosted in a dedicated `files` Blueprint (`file_routes.py`) with injected dependencies
- **Service-layer pattern** — all file business logic lives in `file_service.py`, keeping routes thin
- **Context processors** — notifications and template helpers are injected globally into every template render

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | Flask 3.x |
| Database | SQLite 3 |
| Encryption | AES-256-GCM via `cryptography` |
| Hashing | SHA-256 via `hashlib` + content extraction (`python-docx`, `pypdf`) |
| Email | Flask-Mail (SMTP) |
| CAPTCHA | Pillow (server-side image generation) |
| Frontend CSS | Bootstrap 5.3.3 + custom cybersecurity theme |
| Icons | Font Awesome 6.4.0 |
| Environment | `python-dotenv` |

> **Note:** `python-docx` and `pypdf` are used for `.docx` and `.pdf` content hashing but are not currently listed in `requirements.txt`.

---

## Installation Instructions

### Prerequisites
- Python 3.9+
- pip
- An SMTP account (Gmail, Outlook, etc.) for OTP emails

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/HashGuard.git
   cd HashGuard
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   If you plan to use `.docx` or `.pdf` content hashing, also install:
   ```bash
   pip install python-docx pypdf
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in all required values (see [Configuration](#configuration-env-requirements)).

5. **Initialize the database**
   ```bash
   python create_db.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```
   
   Open `http://localhost:5000` in your browser.

---

## Configuration (.env Requirements)

Copy `.env.example` to `.env` before running. The following variables are required:

| Variable | Required | Description | Generation Command |
|----------|----------|-------------|-------------------|
| `HASHGUARD_SECRET_KEY` | Yes | Flask session signing key | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `AES_ENCRYPTION_KEY` | Yes | Base64-encoded 32-byte AES-256 key | `python -c "import base64, os; print(base64.b64encode(os.urandom(32)).decode())"` |
| `MAIL_SERVER` | Yes | SMTP server hostname | e.g. `smtp.gmail.com` |
| `MAIL_PORT` | Yes | SMTP port | e.g. `587` |
| `MAIL_USE_TLS` | Yes | Use TLS? (`True`/`False`) | — |
| `MAIL_USERNAME` | Yes | Sender email address | — |
| `MAIL_PASSWORD` | Yes | App-specific password / SMTP credential | — |
| `MAIL_DEFAULT_SENDER` | No | Override sender address | Defaults to `MAIL_USERNAME` |

### Application Constants (hardcoded)
- **OTP expiry**: 5 minutes
- **OTP resend cooldown**: 60 seconds
- **Max failed login attempts**: 5
- **Account lockout duration**: 15 minutes
- **Session inactivity timeout**: 30 minutes

---

## Database Overview

HashGuard uses a **SQLite** database (`database/hashguard.db`) with 7 normalized tables and 11 performance indexes.

### Entities

#### Authentication
- **`users`** — registered accounts with hashed passwords, security questions, and account status (`ACTIVE`, `LOCKED`)
- **`pending_registrations`** — staged signups awaiting OTP email verification before promotion to `users`
- **`otp_verification`** — time-limited one-time passwords for registration, login, and password reset flows
- **`login_audit`** — per-attempt records of IP, user-agent, and SUCCESS/FAILED status

#### Files & Storage
- **`files`** — encrypted file metadata: owner, original/stored filename, MIME type, size, dual SHA-256 hashes, status (`ACTIVE`, `MODIFIED`, `DELETED`, `QUARANTINED`), and soft-delete flag
- **`file_audit_logs`** — chronological per-file history of upload, download, verify, delete, and modification events

#### Access Control
- **`access_requests`** — pending and historical access requests with requested permission level (`READ_ONLY`, `READ_WRITE`)
- **`file_permissions`** — active grants with unique `(file_id, user_id)` constraint

#### Monitoring
- **`audit_logs`** — consolidated system events (LOGIN, LOGOUT, COMPARE, UPLOAD, DOWNLOAD, VERIFY, etc.) with IP tracking
- **`notifications`** — per-user notification queue for access requests, approvals, rejections, revocations, tamper alerts, and system alerts

### Indexes
Optimized indexes exist on `user_id`, `owner_id`, `(owner_id, sha256_hash, is_deleted)`, and audit foreign keys to keep permission checks and repository queries fast even as the dataset scales.

---

## Security Features

### Cryptographic Protections
- **AES-256-GCM** for all file data at rest (nonce prepended to ciphertext; authenticated encryption)
- **SHA-256** for both raw integrity verification and normalized content deduplication
- **Werkzeug `generate_password_hash`** for user passwords (PBKDF2-based)
- **SHA-256 hashed security answers** — never stored in plaintext

### Hardened Authentication
- **CAPTCHA** generated with Pillow (noise, grid lines, edge enhancement; ambiguous characters excluded)
- **OTP via email** — 6-digit codes, 5-minute TTL, one-time use, 60-second resend guard
- **Account lockout** — brute-force prevention via timed suspension
- **Session pinning** — 30-minute inactivity timeout; `session.clear()` on logout or expiry

### Input Guardrails
- **File-type allow/deny lists** — rejects executables and other dangerous extensions
- **Path traversal prevention** — `os.path.basename()` used on all uploaded filenames
- **Parameterized SQL** — all queries use bound parameters to prevent injection

### Operational Security
- **Environment-based secrets** — `.env` excluded from git; no credentials in source
- **Audit trail** — immutable-ish logs with IP and user-agent capture for forensic review
- **Soft deletes** — data is never hard-deleted, preserving chain of custody

---

## File Structure

```
HashGuard/
├── .env                        # Runtime secrets (git-ignored)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── app.py                      # Main Flask app (~1,356 lines)
│                               # Routes, decorators, auth, templates
├── create_db.py                # Fresh database initialization
├── file_routes.py              # Files Blueprint (~342 lines)
│                               # Upload, download, verify, delete, replace,
│                               # request-access, permission routes
├── file_service.py             # Business logic layer (~551 lines)
│                               # Encryption, hashing, permissions, audit
├── migrate_db.py               # Schema migration script (~174 lines)
├── requirements.txt            # Python dependencies
├── schema.sql                  # Database DDL (~151 lines)
├── database/
│   └── hashguard.db            # SQLite database file
├── static/
│   ├── css/
│   │   └── style.css           # Dark cybersecurity theme
│   └── js/
│       └── app.js              # Client-side validation, OTP input,
│                               # captcha refresh, drag-and-drop
├── templates/
│   ├── partials/
│   │   └── upload_form.html    # Reusable upload form partial
│   ├── audit_logs.html         # Paginated, searchable system audit
│   ├── compare_file.html       # Content hash comparison tool
│   ├── dashboard.html          # Main repository view + notifications
│   ├── file_details.html       # Metadata, audit history, actions
│   ├── forgot_password.html    # Password reset step 1
│   ├── forgot_password_reset.html  # Password reset step 2
│   ├── login.html              # CAPTCHA + credential login
│   ├── requests.html           # Request center (received / sent / active)
│   ├── request_access.html     # Access request form
│   ├── signup.html             # Registration + CAPTCHA + security Q
│   ├── upload.html             # File upload page
│   └── verify_otp.html         # OTP input with resend cooldown
├── uploads/                    # Encrypted file storage (git-ignored)
└── utils/
    ├── __init__.py
    ├── encryption.py           # AES-256-GCM encrypt/decrypt
    ├── file_hash.py            # SHA-256 + content-aware hashing
    └── file_validator.py       # Filename, extension, size checks
```

---

## Usage Guide

### Getting Started

1. Create an account via `/signup`. You will receive an email OTP; verify it to activate your account.
2. Log in at `/login`. After password verification, a second OTP is sent to your email for session confirmation.
3. Once authenticated, you land on the **Dashboard**, which displays the global file repository.

### Uploading Files
- Navigate to `/upload` or use the dashboard.
- Select a file (allowed types: `pdf`, `txt`, `docx`, `xlsx`, `pptx`, `png`, `jpg`, `jpeg`).
- The file is validated, SHA-256 hashed, encrypted with AES-256-GCM, and stored with a random filename.

### Verifying Integrity
- From the dashboard or file details page, click **Verify Integrity**.
- HashGuard decrypts the file, re-computes the SHA-256 hash, and compares it to the stored value.
- Status updates to `MODIFIED` if the hash mismatches, triggering a tamper alert.

### Sharing Files
- Click **Request Access** on any file owned by another user.
- Select `READ_ONLY` or `READ_WRITE` and optionally add a message.
- The file owner receives a notification and can approve (with chosen permission) or reject the request.
- Once approved, the requester gains access based on the granted permission type.
- Owners can revoke permissions at any time from the **Requests** page.

### Comparing Files
- Use `/compare-file` to upload a local file and check whether its content matches a repository file.
- This performs a content-hash comparison (semantic for text-based files).

### Audit & Monitoring
- Visit `/audit-logs` to browse the consolidated, searchable system audit trail.
- Per-file audit history is visible on each file's detail page.

### Password Recovery
- Go to `/forgot-password`, enter your registered email, then answer your security question and set a new password.

---

## Future Enhancements

Based on the current architecture, the following enhancements would be natural extensions:

- **Role-based access control (RBAC)** — extend the current permission model with roles (Admin, Editor, Viewer)
- **Versioning** — retain file version history instead of overwriting on replacement
- **Quarantine workflow** — leverage the existing `QUARANTINED` status with a review/approval pipeline
- **Batch operations** — bulk upload, verify, and permission grants
- **API layer** — expose core functionality via a REST API for integration with external tools
- **Storage backend abstraction** — swap SQLite for PostgreSQL without changing business logic
- **Automated integrity scheduling** — cron-like background jobs to re-verify all active files nightly
- **Enhanced content hashing** — extend content extraction to additional formats (xlsx, pptx, images)
- **Two-factor authentication (TOTP)** — add authenticator-app support as an alternative to email OTP
- **Log export & retention policies** — CSV/JSON export of audit logs with configurable retention

---
## Author

**Chhavi Ambasta**
**Shafaq Ahmed**
**Khushi Singh**

HashGuard was developed as a cybersecurity-focused file integrity and access management system featuring AES-256 encryption, SHA-256 integrity verification, audit logging, file comparison, and role-based access control.
