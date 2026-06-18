"""
HashGuard Database Initialization Script
Creates the SQLite database and applies schema.sql
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "hashguard.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")


def create_database():
    os.makedirs(DATABASE_DIR, exist_ok=True)

    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as schema_file:
        schema_sql = schema_file.read()

    conn = sqlite3.connect(DATABASE_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database created successfully at: {DATABASE_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_database()
