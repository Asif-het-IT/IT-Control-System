# infrastructure/security/credential_manager.py
"""
Enterprise-grade credential management for Windows deployments.
Uses Windows Credential Manager for secure storage.
"""

from __future__ import annotations
import keyring
from typing import Optional, Dict, Any, List
import json
import logging
import os

logger = logging.getLogger(__name__)

class WindowsCredentialManager:
    """Windows Credential Manager implementation for secure credential storage."""

    SERVICE_NAME = "HET-IT-Control-System"

    def __init__(self):
        """Initialize the credential manager."""
        self._test_credential_manager()

    def _test_credential_manager(self) -> None:
        """Test if Windows Credential Manager is available."""
        try:
            # Try to access keyring
            keyring.get_keyring()
            logger.info("Windows Credential Manager initialized successfully")
        except Exception as e:
            logger.error(f"Windows Credential Manager not available: {e}")
            raise RuntimeError("Windows Credential Manager is required for secure credential storage")

    def store_credential(self, key: str, username: str, password: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store credential securely in Windows Credential Manager.

        Args:
            key: Unique identifier for the credential
            username: Username/email for the credential
            password: Password to store
            metadata: Additional metadata to store

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate inputs
            if not key or not key.strip():
                raise ValueError("Credential key cannot be empty")
            if not username or not username.strip():
                raise ValueError("Username cannot be empty")
            if not password:
                raise ValueError("Password cannot be empty")

            # Prepare credential data
            credential_data = {
                "username": username.strip(),
                "metadata": metadata or {}
            }

            # Store password securely
            keyring.set_password(self.SERVICE_NAME, f"{key}_password", password)

            # Store username and metadata as JSON in a separate entry
            keyring.set_password(self.SERVICE_NAME, f"{key}_data", json.dumps(credential_data))

            logger.info(f"Credential stored successfully for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store credential for {key}: {e}")
            return False

    def get_credential(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve credential from Windows Credential Manager.

        Args:
            key: Unique identifier for the credential

        Returns:
            Dict containing username, password, and metadata, or None if not found
        """
        try:
            if not key or not key.strip():
                return None

            # Retrieve password
            password = keyring.get_password(self.SERVICE_NAME, f"{key}_password")
            if not password:
                logger.debug(f"No password found for key: {key}")
                return None

            # Retrieve username and metadata
            data_json = keyring.get_password(self.SERVICE_NAME, f"{key}_data")
            if not data_json:
                logger.warning(f"Password found but no data for key: {key}")
                return None

            # Parse credential data
            try:
                credential_data = json.loads(data_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid credential data format for key {key}: {e}")
                return None

            return {
                "username": credential_data.get("username", ""),
                "password": password,
                "metadata": credential_data.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Failed to retrieve credential for {key}: {e}")
            return None

    def delete_credential(self, key: str) -> bool:
        """
        Delete credential from Windows Credential Manager.

        Args:
            key: Unique identifier for the credential

        Returns:
            bool: True if deleted, False if not found or error
        """
        try:
            if not key or not key.strip():
                return False

            deleted_count = 0

            # Delete password entry
            try:
                keyring.delete_password(self.SERVICE_NAME, f"{key}_password")
                deleted_count += 1
            except keyring.errors.PasswordDeleteError:
                pass  # Password entry doesn't exist

            # Delete data entry
            try:
                keyring.delete_password(self.SERVICE_NAME, f"{key}_data")
                deleted_count += 1
            except keyring.errors.PasswordDeleteError:
                pass  # Data entry doesn't exist

            if deleted_count > 0:
                logger.info(f"Credential deleted for key: {key}")
                return True
            else:
                logger.debug(f"No credential found to delete for key: {key}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete credential for {key}: {e}")
            return False

    def update_credential(self, key: str, username: Optional[str] = None,
                         password: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update existing credential.

        Args:
            key: Unique identifier for the credential
            username: New username (optional)
            password: New password (optional)
            metadata: New metadata (optional)

        Returns:
            bool: True if updated successfully
        """
        try:
            # Get existing credential
            existing = self.get_credential(key)
            if not existing:
                logger.error(f"Cannot update non-existent credential: {key}")
                return False

            # Update fields
            new_username = username if username is not None else existing["username"]
            new_password = password if password is not None else existing["password"]
            new_metadata = metadata if metadata is not None else existing["metadata"]

            # Store updated credential
            return self.store_credential(key, new_username, new_password, new_metadata)

        except Exception as e:
            logger.error(f"Failed to update credential for {key}: {e}")
            return False

    def list_credentials(self) -> List[str]:
        """
        List all stored credential keys.

        Note: Windows Credential Manager doesn't provide direct listing,
        so this returns an empty list. Use get_credential() to check existence.

        Returns:
            List of credential keys (empty for Windows Credential Manager)
        """
        # Windows Credential Manager doesn't expose credential listing for security reasons
        logger.debug("Credential listing not supported by Windows Credential Manager")
        return []

    def credential_exists(self, key: str) -> bool:
        """
        Check if a credential exists.

        Args:
            key: Unique identifier for the credential

        Returns:
            bool: True if credential exists
        """
        return self.get_credential(key) is not None

    def get_credential_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get credential information without password.

        Args:
            key: Unique identifier for the credential

        Returns:
            Dict with username and metadata, or None if not found
        """
        credential = self.get_credential(key)
        if not credential:
            return None

        return {
            "username": credential["username"],
            "metadata": credential["metadata"]
        }

    def migrate_from_plaintext(self, config_file: str) -> Dict[str, bool]:
        """
        Migrate credentials from plaintext config file to secure storage.

        Args:
            config_file: Path to plaintext config file

        Returns:
            Dict mapping credential keys to migration success status
        """
        migration_results = {}

        try:
            if not os.path.exists(config_file):
                logger.warning(f"Config file not found: {config_file}")
                return migration_results

            with open(config_file, 'r') as f:
                config_data = json.load(f)

            # Look for credentials section
            credentials = config_data.get("credentials", {})

            for key, cred_data in credentials.items():
                try:
                    username = cred_data.get("username", "")
                    password = cred_data.get("password", "")
                    metadata = cred_data.get("metadata", {})

                    if username and password:
                        success = self.store_credential(key, username, password, metadata)
                        migration_results[key] = success
                        if success:
                            logger.info(f"Migrated credential: {key}")
                        else:
                            logger.error(f"Failed to migrate credential: {key}")
                    else:
                        logger.warning(f"Skipping incomplete credential: {key}")

                except Exception as e:
                    logger.error(f"Error migrating credential {key}: {e}")
                    migration_results[key] = False

        except Exception as e:
            logger.error(f"Error during credential migration: {e}")

        return migration_results


# Global instance for easy access
_credential_manager = None

def get_credential_manager() -> WindowsCredentialManager:
    """Get the global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = WindowsCredentialManager()
    return _credential_manager
<parameter name="filePath">d:\My App\infrastructure\security\credential_manager.py