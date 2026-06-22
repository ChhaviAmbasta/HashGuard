"""
HashGuard Database Migration Script
Upgrades an existing Phase-1 database to the enterprise schema.
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "hashguard.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def migrate_users_table(conn):
    if not table_exists(conn, "users"):
        return

    if column_exists(conn, "users", "password") and not column_exists(conn, "users", "password_hash"):
        conn.execute("ALTER TABLE users RENAME COLUMN password TO password_hash")

    new_columns = [
        ("security_question", "TEXT NOT NULL DEFAULT 'q1'"),
        ("security_answer_hash", "TEXT NOT NULL DEFAULT ''"),
        ("email_verified", "INTEGER NOT NULL DEFAULT 0"),
        ("last_login", "TIMESTAMP"),
        ("account_status", "TEXT NOT NULL DEFAULT 'ACTIVE'"),
        ("failed_attempts", "INTEGER NOT NULL DEFAULT 0"),
        ("locked_until", "TIMESTAMP"),
    ]

    for column_name, column_def in new_columns:
        if not column_exists(conn, "users", column_name):
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")

    conn.execute(
        """
        UPDATE users
        SET email_verified = 1,
            account_status = 'ACTIVE'
        WHERE email_verified = 0
          AND security_answer_hash = ''
        """
    )


def migrate_file_storage_tables(conn):
    if not table_exists(conn, "files"):
        conn.execute(
            """
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                file_extension TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                mime_type TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                content_hash TEXT,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_verified TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                is_deleted INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
            """
        )
    else:
        if not column_exists(conn, "files", "content_hash"):
            conn.execute("ALTER TABLE files ADD COLUMN content_hash TEXT")

    if not table_exists(conn, "file_audit_logs"):
        conn.execute(
            """
            CREATE TABLE file_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_files_owner ON files(owner_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_owner_hash ON files(owner_id, sha256_hash, is_deleted)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_file_audit_file ON file_audit_logs(file_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_file_audit_user ON file_audit_logs(user_id)")


def migrate_centralized_storage():
    """
    Move files from legacy uploads/user_<id>/ folders into the centralized uploads/ directory.
    Preserves existing database records; only the on-disk layout changes.
    """
    upload_root = os.path.join(BASE_DIR, "uploads")
    if not os.path.isdir(upload_root):
        os.makedirs(upload_root, exist_ok=True)
        return 0

    moved_count = 0
    for entry in os.listdir(upload_root):
        user_dir = os.path.join(upload_root, entry)
        if not entry.startswith("user_") or not os.path.isdir(user_dir):
            continue

        for filename in os.listdir(user_dir):
            source_path = os.path.join(user_dir, filename)
            if not os.path.isfile(source_path):
                continue

            destination_path = os.path.join(upload_root, filename)
            if os.path.exists(destination_path):
                destination_path = os.path.join(upload_root, f"{entry}_{filename}")

            os.replace(source_path, destination_path)
            moved_count += 1

        try:
            os.rmdir(user_dir)
        except OSError:
            pass

    return moved_count


def apply_new_tables(conn):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        schema_sql = schema_file.read()
    conn.executescript(schema_sql)


def migrate_database():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    if not os.path.exists(DATABASE_PATH):
        print("No existing database found. Run create_db.py instead.")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        migrate_users_table(conn)
        apply_new_tables(conn)
        migrate_file_storage_tables(conn)
        conn.commit()
        moved_files = migrate_centralized_storage()
        print(f"Database migrated successfully at: {DATABASE_PATH}")
        print(f"Centralized storage migration moved {moved_files} file(s).")
        print(f"Migration completed at: {datetime.utcnow().isoformat()} UTC")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
