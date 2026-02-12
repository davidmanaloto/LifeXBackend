import os
import base64
from cryptography.fernet import Fernet
from django.conf import settings

class EncryptionManager:
    """
    Utility class for encrypting and decrypting sensitive data.
    Uses Fernet symmetric encryption.
    """
    
    def __init__(self, key=None):
        if key is None:
            # Try to get key from settings, else generate one for testing (NOT FOR PRODUCTION)
            key = getattr(settings, 'ENCRYPTION_KEY', None)
            if not key:
                # Fallback to SECRET_KEY if ENCRYPTION_KEY is not set
                # We need it to be 32 bytes and base64 encoded for Fernet
                # This is a fallback and should be replaced by a proper key in .env
                key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32, b'0'))
        
        if isinstance(key, str):
            key = key.encode()
            
        self.fernet = Fernet(key)

    def encrypt(self, data):
        """
        Encrypts a string or bytes data.
        Returns the encrypted data as a string.
        """
        if data is None:
            return None
            
        if isinstance(data, str):
            data = data.encode()
            
        encrypted_data = self.fernet.encrypt(data)
        return encrypted_data.decode()

    def decrypt(self, encrypted_data):
        """
        Decrypts an encrypted string or bytes.
        Returns the decrypted data as a string.
        """
        if encrypted_data is None:
            return None
            
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode()
            
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data)
            return decrypted_data.decode()
        except Exception as e:
            # Log error or handle decryption failure
            print(f"Decryption failed: {e}")
            return None

# Singleton instance
encryption_manager = EncryptionManager()
