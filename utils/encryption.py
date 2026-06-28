"""
HashGuard - AES-256-GCM Encryption Utilities
Path: utils/encryption.py
Purpose: Encrypt and decrypt files using AES-256-GCM for secure file storage.
"""

import os
from base64 import b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag


def get_encryption_key():
    key_b64 = os.environ.get("AES_ENCRYPTION_KEY")
    if not key_b64:
        raise ValueError("AES_ENCRYPTION_KEY not set in environment. Generate a key with: python -c \"from cryptography.fernet import Fernet; import base64; import os; key = base64.b64encode(os.urandom(32)); print(key.decode())\"")
    return key_b64


def get_aesgcm():
    key_b64 = get_encryption_key()
    key = b64decode(key_b64)
    return AESGCM(key)


def encrypt_bytes(data: bytes) -> bytes:
    aesgcm = get_aesgcm()
    nonce = os.urandom(12)
    encrypted = aesgcm.encrypt(nonce, data, None)
    return nonce + encrypted


def decrypt_bytes(encrypted_data: bytes) -> bytes:
    try:
        aesgcm = get_aesgcm()
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)
    except (InvalidTag, Exception):
        # Fallback for unencrypted legacy files stored before encryption was enabled
        return encrypted_data


def encrypt_file_from_stream(file_stream) -> tuple:
    data = file_stream.read()
    file_stream.seek(0)
    encrypted = encrypt_bytes(data)
    return encrypted


def decrypt_file_to_stream(encrypted_data: bytes) -> bytes:
    return decrypt_bytes(encrypted_data)