"""
HashGuard - Secure File Storage Service
Path: file_service.py
Purpose: Business logic for file uploads, global repository listing, ownership checks,
         duplicate detection, integrity verification, soft deletes, and audit logging.
"""

import mimetypes
import os
import secrets
from datetime import datetime
from io import BytesIO

from utils.encryption import decrypt_bytes, encrypt_bytes
from utils.file_hash import compute_sha256_from_path, compute_sha256_from_stream, compute_content_hash_from_stream
from utils.file_validator import validate_upload

FILE_STATUS_ACTIVE = "ACTIVE"
FILE_STATUS_MODIFIED = "MODIFIED"
FILE_STATUS_DELETED = "DELETED"
FILE_STATUS_QUARANTINED = "QUARANTINED"

AUDIT_UPLOAD = "UPLOAD"
AUDIT_DELETE = "DELETE"
AUDIT_DOWNLOAD = "DOWNLOAD"
AUDIT_VERIFY = "VERIFY"
AUDIT_MODIFICATION_DETECTED = "MODIFICATION_DETECTED"


def get_upload_root(base_dir):
    return os.path.join(base_dir, "uploads")


def ensure_upload_dir(upload_root):
    os.makedirs(upload_root, exist_ok=True)
    return upload_root


def generate_stored_filename(extension):
    return f"{secrets.token_hex(16)}.{extension}"


def guess_mime_type(original_filename, extension):
    mime_type, _ = mimetypes.guess_type(original_filename)
    if mime_type:
        return mime_type
    fallback_map = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return fallback_map.get(extension, "application/octet-stream")


def format_file_size(num_bytes):
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    if num_bytes < 1024 * 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} MB"
    return f"{num_bytes / (1024 * 1024 * 1024):.2f} GB"


def truncate_hash(sha256_hash, visible_chars=12):
    if not sha256_hash:
        return ""
    if len(sha256_hash) <= visible_chars:
        return sha256_hash
    return f"{sha256_hash[:visible_chars]}..."


def log_file_audit(conn, file_id, user_id, action, details, timestamp=None):
    conn.execute(
        """
        INSERT INTO file_audit_logs (file_id, user_id, action, timestamp, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (file_id, user_id, action, timestamp or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), details),
    )


def user_has_duplicate_file(conn, owner_id, sha256_hash):
    row = conn.execute(
        """
        SELECT id
        FROM files
        WHERE owner_id = ?
          AND sha256_hash = ?
          AND is_deleted = 0
        LIMIT 1
        """,
        (owner_id, sha256_hash),
    ).fetchone()
    return row is not None


def user_has_duplicate_content(conn, owner_id, content_hash):
    row = conn.execute(
        """
        SELECT id
        FROM files
        WHERE owner_id = ?
          AND content_hash = ?
          AND is_deleted = 0
        LIMIT 1
        """,
        (owner_id, content_hash),
    ).fetchone()
    return row is not None


def get_owned_file(conn, file_id, owner_id, include_deleted=False):
    if include_deleted:
        query = """
            SELECT f.*, u.username AS owner_username
            FROM files f
            INNER JOIN users u ON u.id = f.owner_id
            WHERE f.id = ? AND f.owner_id = ?
        """
    else:
        query = """
            SELECT f.*, u.username AS owner_username
            FROM files f
            INNER JOIN users u ON u.id = f.owner_id
            WHERE f.id = ? AND f.owner_id = ? AND f.is_deleted = 0
        """

    return conn.execute(query, (file_id, owner_id)).fetchone()


def get_file_by_id(conn, file_id, include_deleted=False):
    if include_deleted:
        query = """
            SELECT f.*, u.username AS owner_username
            FROM files f
            INNER JOIN users u ON u.id = f.owner_id
            WHERE f.id = ?
        """
    else:
        query = """
            SELECT f.*, u.username AS owner_username
            FROM files f
            INNER JOIN users u ON u.id = f.owner_id
            WHERE f.id = ? AND f.is_deleted = 0
        """

    return conn.execute(query, (file_id,)).fetchone()


def list_all_files(conn):
    return conn.execute(
        """
        SELECT f.*, u.username AS owner_username
        FROM files f
        INNER JOIN users u ON u.id = f.owner_id
        WHERE f.is_deleted = 0
        ORDER BY f.upload_time DESC
        """
    ).fetchall()


def is_file_owner(file_record, user_id):
    return file_record["owner_id"] == user_id


def get_file_audit_logs(conn, file_id):
    file_record = get_file_by_id(conn, file_id, include_deleted=True)
    if not file_record:
        return None, []

    logs = conn.execute(
        """
        SELECT *
        FROM file_audit_logs
        WHERE file_id = ?
        ORDER BY timestamp DESC
        """,
        (file_id,),
    ).fetchall()
    return file_record, logs


def get_file_absolute_path(upload_root, stored_filename, owner_id=None):
    """
    Resolve the on-disk path for a stored file.
    Checks the centralized uploads/ directory first, then legacy user_* folders.
    """
    central_path = os.path.join(upload_root, stored_filename)
    if os.path.isfile(central_path):
        return central_path

    if owner_id is not None:
        legacy_path = os.path.join(upload_root, f"user_{owner_id}", stored_filename)
        if os.path.isfile(legacy_path):
            return legacy_path

    return central_path


def store_uploaded_file(upload_root, uploaded_file, extension):
    upload_dir = ensure_upload_dir(upload_root)
    stored_filename = generate_stored_filename(extension)
    absolute_path = os.path.join(upload_dir, stored_filename)
    uploaded_file.seek(0)
    data = uploaded_file.read()
    encrypted_data = encrypt_bytes(data)
    with open(absolute_path, "wb") as f:
        f.write(encrypted_data)
    return stored_filename, absolute_path


def create_file_record(
    conn,
    owner_id,
    original_filename,
    stored_filename,
    extension,
    file_size,
    mime_type,
    sha256_hash,
    content_hash,
    upload_time,
):
    cursor = conn.execute(
        """
        INSERT INTO files (
            owner_id,
            original_filename,
            stored_filename,
            file_extension,
            file_size,
            mime_type,
            sha256_hash,
            content_hash,
            upload_time,
            last_verified,
            status,
            is_deleted
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            original_filename,
            stored_filename,
            extension,
            file_size,
            mime_type,
            sha256_hash,
            content_hash,
            upload_time,
            upload_time,
            FILE_STATUS_ACTIVE,
            0,
        ),
    )
    return cursor.lastrowid


def process_file_upload(conn, upload_root, owner_id, uploaded_file, upload_time):
    if uploaded_file is None or not uploaded_file.filename:
        return False, "No file selected.", None

    original_filename = os.path.basename(uploaded_file.filename.strip())
    uploaded_file.seek(0, os.SEEK_END)
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)

    is_valid, error_message, extension = validate_upload(original_filename, file_size)
    if not is_valid:
        return False, error_message, None

    sha256_hash = compute_sha256_from_stream(uploaded_file)
    content_hash = compute_content_hash_from_stream(uploaded_file, extension)

    if user_has_duplicate_file(conn, owner_id, sha256_hash):
        return False, "Duplicate file detected.", None

    if user_has_duplicate_content(conn, owner_id, content_hash):
        return False, "Duplicate content detected. This file already exists in the repository.", None

    stored_filename, _ = store_uploaded_file(upload_root, uploaded_file, extension)
    with open(get_file_absolute_path(upload_root, stored_filename, owner_id), "rb") as f:
        disk_hash = compute_sha256_from_stream(BytesIO(decrypt_bytes(f.read())))
    if disk_hash != sha256_hash:
        absolute_path = get_file_absolute_path(upload_root, stored_filename, owner_id)
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
        return False, "File integrity check failed during upload. Please try again.", None

    mime_type = guess_mime_type(original_filename, extension)
    file_id = create_file_record(
        conn,
        owner_id,
        original_filename,
        stored_filename,
        extension,
        file_size,
        mime_type,
        sha256_hash,
        content_hash,
        upload_time,
    )
    log_file_audit(
        conn,
        file_id,
        owner_id,
        AUDIT_UPLOAD,
        f"Uploaded '{original_filename}' ({format_file_size(file_size)}). SHA-256: {sha256_hash}",
        upload_time,
    )
    return True, "File uploaded successfully.", file_id


def soft_delete_file(conn, file_record, owner_id, timestamp):
    conn.execute(
        """
        UPDATE files
        SET is_deleted = 1,
            status = ?
        WHERE id = ?
          AND owner_id = ?
        """,
        (FILE_STATUS_DELETED, file_record["id"], owner_id),
    )
    log_file_audit(
        conn,
        file_record["id"],
        owner_id,
        AUDIT_DELETE,
        f"Soft deleted '{file_record['original_filename']}'.",
        timestamp,
    )


def verify_file_integrity(conn, upload_root, file_record, actor_user_id, timestamp):
    absolute_path = get_file_absolute_path(
        upload_root, file_record["stored_filename"], file_record["owner_id"]
    )
    if not os.path.isfile(absolute_path):
        return False, "Stored file could not be located on disk.", file_record["status"], None

    with open(absolute_path, "rb") as f:
        encrypted_data = f.read()
    current_hash = compute_sha256_from_stream(BytesIO(decrypt_bytes(encrypted_data)))
    stored_hash = file_record["sha256_hash"]

    if current_hash == stored_hash:
        new_status = FILE_STATUS_ACTIVE
        details = (
            f"Integrity verified for '{file_record['original_filename']}'. "
            f"Hash match confirmed."
        )
        conn.execute(
            """
            UPDATE files
            SET status = ?,
                last_verified = ?
            WHERE id = ?
            """,
            (new_status, timestamp, file_record["id"]),
        )
        log_file_audit(conn, file_record["id"], actor_user_id, AUDIT_VERIFY, details, timestamp)
        return True, "File integrity verified. Status: ACTIVE.", new_status, current_hash

    new_status = FILE_STATUS_MODIFIED
    modification_details = (
        f"Modification detected for '{file_record['original_filename']}'. "
        f"Expected SHA-256: {stored_hash}. Current SHA-256: {current_hash}."
    )
    conn.execute(
        """
        UPDATE files
        SET status = ?,
            last_verified = ?
        WHERE id = ?
        """,
        (new_status, timestamp, file_record["id"]),
    )
    log_file_audit(
        conn,
        file_record["id"],
        actor_user_id,
        AUDIT_MODIFICATION_DETECTED,
        modification_details,
        timestamp,
    )
    log_file_audit(
        conn,
        file_record["id"],
        actor_user_id,
        AUDIT_VERIFY,
        "Integrity verification completed with hash mismatch.",
        timestamp,
    )
    return (
        True,
        "Integrity mismatch detected. Status updated to MODIFIED.",
        new_status,
        current_hash,
    )


def record_download_audit(conn, file_record, actor_user_id, timestamp):
    log_file_audit(
        conn,
        file_record["id"],
        actor_user_id,
        AUDIT_DOWNLOAD,
        f"Downloaded '{file_record['original_filename']}'.",
        timestamp,
    )


def get_user_file_permission(conn, file_id, user_id):
    """
    Returns the active permission type ('READ_ONLY', 'READ_WRITE', or 'OWNER') for the user on the file,
    or None if no permission.
    """
    row = conn.execute("SELECT owner_id FROM files WHERE id = ? AND is_deleted = 0", (file_id,)).fetchone()
    if not row:
        return None
    if row["owner_id"] == user_id:
        return "OWNER"

    perm_row = conn.execute(
        """
        SELECT permission_type 
        FROM file_permissions 
        WHERE file_id = ? AND user_id = ?
        """,
        (file_id, user_id),
    ).fetchone()
    
    if perm_row:
        return perm_row["permission_type"]
        
    return None


def has_read_permission(conn, file_id, user_id):
    perm = get_user_file_permission(conn, file_id, user_id)
    return perm in ("OWNER", "READ_ONLY", "READ_WRITE")


def has_write_permission(conn, file_id, user_id):
    perm = get_user_file_permission(conn, file_id, user_id)
    return perm in ("OWNER", "READ_WRITE")


def get_pending_request(conn, file_id, user_id):
    """
    Returns the pending access request record if any.
    """
    return conn.execute(
        """
        SELECT * FROM access_requests
        WHERE file_id = ? AND requester_id = ? AND status = 'PENDING'
        LIMIT 1
        """,
        (file_id, user_id)
    ).fetchone()


def process_file_replacement(conn, upload_root, file_record, uploaded_file, actor_id, timestamp):
    if uploaded_file is None or not uploaded_file.filename:
        return False, "No file selected."

    original_filename = os.path.basename(uploaded_file.filename.strip())
    uploaded_file.seek(0, os.SEEK_END)
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)

    is_valid, error_message, extension = validate_upload(original_filename, file_size)
    if not is_valid:
        return False, error_message

    sha256_hash = compute_sha256_from_stream(uploaded_file)
    content_hash = compute_content_hash_from_stream(uploaded_file, extension)

    print(f"[DEBUG replace] uploaded_size={file_size} sha256={sha256_hash}")

    if user_has_duplicate_content(conn, file_record["owner_id"], content_hash):
        existing = conn.execute(
            """
            SELECT id, original_filename FROM files
            WHERE owner_id = ? AND content_hash = ? AND is_deleted = 0 AND id != ?
            LIMIT 1
            """,
            (file_record["owner_id"], content_hash, file_record["id"]),
        ).fetchone()
        if existing:
            return False, "Duplicate content detected. This file already exists as '{}'.".format(existing["original_filename"])

    stored_filename, absolute_path = store_uploaded_file(upload_root, uploaded_file, extension)
    print(f"[DEBUG replace] stored_path={absolute_path}")

    with open(absolute_path, "rb") as f:
        encrypted_data = f.read()
    print(f"[DEBUG replace] encrypted_size={len(encrypted_data)}")
    decrypted_data = decrypt_bytes(encrypted_data)
    print(f"[DEBUG replace] decrypted_size={len(decrypted_data)}")
    disk_hash = compute_sha256_from_stream(BytesIO(decrypted_data))
    print(f"[DEBUG replace] disk_sha256={disk_hash}")
    if disk_hash != sha256_hash:
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
        return False, "File integrity check failed during replacement upload."

    try:
        old_absolute_path = get_file_absolute_path(
            upload_root, file_record["stored_filename"], file_record["owner_id"]
        )
        if os.path.exists(old_absolute_path) and os.path.isfile(old_absolute_path):
            os.remove(old_absolute_path)
    except Exception:
        pass

    mime_type = guess_mime_type(original_filename, extension)
    conn.execute(
        """
        UPDATE files
        SET stored_filename = ?,
            file_extension = ?,
            file_size = ?,
            mime_type = ?,
            sha256_hash = ?,
            content_hash = ?,
            last_verified = ?,
            status = 'ACTIVE'
        WHERE id = ?
        """,
        (stored_filename, extension, file_size, mime_type, sha256_hash, content_hash, timestamp, file_record["id"]),
    )

    log_file_audit(
        conn,
        file_record["id"],
        actor_id,
        AUDIT_UPLOAD,
        f"Replaced file contents of '{file_record['original_filename']}' with '{original_filename}'. New SHA-256: {sha256_hash}",
        timestamp,
    )
    return True, "File contents replaced successfully."

