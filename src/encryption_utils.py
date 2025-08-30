import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from models import Message
from utils import str_to_bool

logger = logging.getLogger(__name__)

ENCRYPTION_ENABLED_ENV = 'ENCRYPTION_ENABLED'
ENCRYPTION_KEY_ENV = 'ENCRYPTION_KEY'
ENCRYPTED_PREFIX = 'ENC:'


def is_encryption_enabled() -> bool:
    """
    Check if encryption is enabled via environment variable
    @return: True if encryption is enabled, False otherwise
    """
    return str_to_bool(os.getenv(ENCRYPTION_ENABLED_ENV, False))


def get_encryption_key() -> Optional[bytes]:
    """
    Get the encryption key from environment variables
    @return: The encryption key as bytes, or None if not configured
    """
    key_str = os.getenv(ENCRYPTION_KEY_ENV)
    if not key_str:
        return None
    
    try:
        return key_str.encode()
    except Exception as e:
        logger.error(f"Failed to decode encryption key: {e}")
        return None


def generate_key() -> str:
    """
    Generate a new Fernet encryption key
    @return: Base64-encoded key as string
    """
    key: bytes = Fernet.generate_key()
    return key.decode()


def encrypt_message_content(content: str) -> str:
    """
    Encrypt message content if encryption is enabled
    @param content: The content string to encrypt
    @return: Encrypted content string, or original content if encryption disabled/failed
    """
    if not is_encryption_enabled():
        return content
    
    encryption_key: bytes | None = get_encryption_key()
    if not encryption_key:
        logger.warning("Encryption enabled but no key configured. Storing content unencrypted.")
        return content
    
    try:
        fernet = Fernet(encryption_key)
        encrypted_content: bytes = fernet.encrypt(content.encode())
        encrypted_content_str: str = ENCRYPTED_PREFIX + encrypted_content.decode()
        return encrypted_content_str
    except Exception as e:
        logger.error(f"Failed to encrypt content: {e}")
        return content


def decrypt_message_content(content: str) -> str:
    """
    Decrypt message content if it's encrypted
    @param content: The content string to decrypt
    @return: Decrypted content string, or original content if not encrypted/failed
    """
    if not is_content_encrypted(content):
        return content
    
    encryption_key = get_encryption_key()
    if not encryption_key:
        logger.warning("Encrypted content found but no key configured. Returning encrypted content.")
        return content
    
    try:
        encrypted_content: str = content[len(ENCRYPTED_PREFIX):]
        
        fernet = Fernet(encryption_key)
        decrypted_content = fernet.decrypt(encrypted_content).decode()
        return decrypted_content
    except (InvalidToken, Exception) as e:
        logger.error(f"Failed to decrypt content: {e}")
        return content


def is_content_encrypted(content: str) -> bool:
    """
    Check if content is encrypted
    @param content: The content string to check
    @return: True if the content is encrypted, False otherwise
    """
    return content.startswith(ENCRYPTED_PREFIX)
