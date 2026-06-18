"""
HashGuard - File Hash Utilities
Path: utils/file_hash.py
Purpose: Compute and compare SHA-256 digests for uploaded files to support
         integrity verification and duplicate detection.
"""

import hashlib


def compute_sha256_from_path(file_path, chunk_size=8192):
    """
    Read a file from disk in chunks and return its SHA-256 hex digest.
    """
    digest = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        while True:
            chunk = file_handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def compute_sha256_from_stream(file_stream, chunk_size=8192):
    """
    Compute SHA-256 from an uploaded file stream without persisting it first.
    Resets the stream position to the beginning after hashing.
    """
    digest = hashlib.sha256()
    while True:
        chunk = file_stream.read(chunk_size)
        if not chunk:
            break
        digest.update(chunk)
    file_stream.seek(0)
    return digest.hexdigest()
