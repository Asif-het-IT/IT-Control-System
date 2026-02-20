# app/security/credentials.py
"""
Windows Credential Manager for secure credential storage.
Machine-level storage for Windows services.
"""

import keyring
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class CredentialManager:
    """Windows Credential Manager wrapper for secure storage."""

    SERVICE_NAME = "HET-IT-Control-System"

    def __init__(self):
        """Initialize credential manager."""
        try:
            keyring.get_keyring()
            logger.info("Windows Credential Manager initialized")
        except Exception as e:
            logger.error(f"Credential Manager not available: {e}")
            raise RuntimeError("Windows Credential Manager required")

    def store(self, key: str, username: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store credentials securely."""
        try:
            if not key or not username or not password:
                raise ValueError("Key, username, and password are required")

            # Store password
            keyring.set_password(self.SERVICE_NAME, f"{key}_password", password)

            # Store username and metadata
            data = {"username": username, "metadata": metadata or {}}
            keyring.set_password(self.SERVICE_NAME, f"{key}_data", json.dumps(data))

            logger.info(f"Credentials stored for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store credentials for {key}: {e}")
            return False

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve credentials."""
        try:
            if not key:
                return None

            # Get password
            password = keyring.get_password(self.SERVICE_NAME, f"{key}_password")
            if not password:
                return None

            # Get data
            data_json = keyring.get_password(self.SERVICE_NAME, f"{key}_data")
            if not data_json:
                return None

            data = json.loads(data_json)
            return {
                "username": data["username"],
                "password": password,
                "metadata": data.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Failed to retrieve credentials for {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete credentials."""
        try:
            if not key:
                return False

            deleted = 0

            # Delete password
            try:
                keyring.delete_password(self.SERVICE_NAME, f"{key}_password")
                deleted += 1
            except:
                pass

            # Delete data
            try:
                keyring.delete_password(self.SERVICE_NAME, f"{key}_data")
                deleted += 1
            except:
                pass

            if deleted > 0:
                logger.info(f"Credentials deleted for key: {key}")
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete credentials for {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if credentials exist."""
        return self.get(key) is not None

    def update(self, key: str, username: Optional[str] = None,
               password: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update existing credentials."""
        current = self.get(key)
        if not current:
            return False

        new_username = username if username else current["username"]
        new_password = password if password else current["password"]
        new_metadata = metadata if metadata else current["metadata"]

        return self.store(key, new_username, new_password, new_metadata)


# Global instance
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager