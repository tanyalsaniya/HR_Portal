# apps/common/encryption.py
import os
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # Fallback key for development if env is not loaded properly
    ENCRYPTION_KEY = 'ISq5vz8Emu8Lor32m0G-c10_hAJwIg_Ab30m_l4W2hQ='

fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

def encrypt_value(value):
    """
    Encrypts a string value. Returns the encrypted ciphertext string.
    """
    if value is None:
        return None
    value_str = str(value).strip()
    if not value_str:
        return ""
    encrypted_bytes = fernet.encrypt(value_str.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_value(encrypted_str):
    """
    Decrypts an encrypted ciphertext string. Returns the plaintext string.
    """
    if not encrypted_str:
        return encrypted_str
    try:
        # Check if it is a valid Fernet token format (Fernet tokens start with gAAAAA)
        if isinstance(encrypted_str, str) and encrypted_str.startswith('gAAAAA'):
            decrypted_bytes = fernet.decrypt(encrypted_str.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        return encrypted_str
    except Exception:
        # Fallback if decryption fails (e.g., if it's already plaintext)
        return encrypted_str
