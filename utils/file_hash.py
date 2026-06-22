"""
HashGuard - File Hash Utilities
Path: utils/file_hash.py
Purpose: Compute and compare SHA-256 digests for uploaded files to support
         integrity verification and duplicate detection.
"""

import hashlib
import io


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


def compute_content_hash_from_stream(file_stream, extension):
    """
    Compute a content-based hash that ignores metadata and focuses on visible content.
    Supports TXT, DOCX, and PDF files.
    Returns the SHA-256 hex digest of the normalized content.
    """
    file_stream.seek(0)
    ext = (extension or "").lower().lstrip(".")
    content_text = ""

    if ext == "txt":
        content_text = _extract_txt(file_stream)
    elif ext == "docx":
        content_text = _extract_docx(file_stream)
    elif ext == "pdf":
        content_text = _extract_pdf(file_stream)
    else:
        content_text = _extract_fallback(file_stream)

    normalized = _normalize_text(content_text)
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    print(f"[DEBUG content_hash] ext={ext} raw_len={len(content_text)} norm_len={len(normalized)} hash={content_hash}")
    return content_hash


def _extract_txt(file_stream):
    try:
        return file_stream.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_docx(file_stream):
    try:
        from docx import Document
        file_stream.seek(0)
        document = Document(file_stream)
        paragraphs = [p.text for p in document.paragraphs if p.text]
        return "\n".join(paragraphs)
    except Exception:
        return _extract_fallback(file_stream)


def _extract_pdf(file_stream):
    try:
        from pypdf import PdfReader
        file_stream.seek(0)
        reader = PdfReader(file_stream)
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n".join(pages)
    except Exception:
        return _extract_fallback(file_stream)


def _extract_fallback(file_stream):
    try:
        file_stream.seek(0)
        return file_stream.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def _normalize_text(text):
    normalized = " ".join(text.lower().split())
    print(f"[DEBUG normalize_text] raw_len={len(text)} norm_len={len(normalized)} sample={normalized[:80]!r}")
    return normalized
