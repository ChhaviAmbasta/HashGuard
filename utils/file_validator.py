"""
HashGuard - File Validation Utilities
Path: utils/file_validator.py
Purpose: Enforce upload restrictions including allowed/blocked extensions
         and basic filename safety checks. No application-level size limits.
"""

import os

ALLOWED_EXTENSIONS = frozenset(
    {"pdf", "txt", "docx", "xlsx", "pptx", "png", "jpg", "jpeg"}
)

BLOCKED_EXTENSIONS = frozenset({"exe", "bat", "cmd", "msi", "sh", "apk"})


def extract_extension(filename):
    """Return the lowercase extension without the leading dot."""
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower().strip()


def validate_filename(filename):
    """
    Validate that a filename is present, safe, and uses an allowed extension.
    Returns (is_valid, error_message, extension).
    """
    if not filename or not filename.strip():
        return False, "No file selected.", ""

    basename = os.path.basename(filename.strip())
    if basename in ("", ".", ".."):
        return False, "Invalid filename.", ""

    extension = extract_extension(basename)
    if not extension:
        return False, "File must have a valid extension.", extension

    if extension in BLOCKED_EXTENSIONS:
        return False, f"File type '.{extension}' is not permitted for security reasons.", extension

    if extension not in ALLOWED_EXTENSIONS:
        allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
        return False, f"File type '.{extension}' is not allowed. Allowed types: {allowed_list}.", extension

    return True, "", extension


def validate_upload(filename, file_size):
    """
    Run upload validation for filename and non-empty content.
    Returns (is_valid, error_message, extension).
    """
    is_valid, error_message, extension = validate_filename(filename)
    if not is_valid:
        return False, error_message, extension

    if file_size <= 0:
        return False, "Uploaded file is empty.", extension

    return True, "", extension
