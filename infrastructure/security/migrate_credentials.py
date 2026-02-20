# infrastructure/security/migrate_credentials.py
"""
Migration script to move plaintext credentials to secure Windows Credential Manager storage.
Run this once to migrate existing credentials from config files.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from infrastructure.security.credential_manager import get_credential_manager

def migrate_email_credentials():
    """Migrate email credentials from settings."""
    print("🔐 Migrating email credentials...")

    try:
        from app.config.settings import get_config
        config = get_config()

        # Check if email credentials exist
        if hasattr(config, 'email') and config.email.smtp_username and config.email.smtp_password:
            credential_manager = get_credential_manager()

            # Store email credentials securely
            success = credential_manager.store_credential(
                key="email_smtp",
                username=config.email.smtp_username,
                password=config.email.smtp_password,
                metadata={
                    "host": config.email.smtp_host,
                    "port": config.email.smtp_port,
                    "tls": config.email.smtp_tls,
                    "type": "smtp"
                }
            )

            if success:
                print("✅ Email credentials migrated successfully")
                print("   Key: email_smtp")
                print("   Username: {}".format(config.email.smtp_username))
                return True
            else:
                print("❌ Failed to migrate email credentials")
                return False
        else:
            print("ℹ️  No email credentials found in config")
            return True

    except Exception as e:
        print(f"❌ Error migrating email credentials: {e}")
        return False

def migrate_from_json_file(json_file_path: str):
    """Migrate credentials from a JSON file."""
    print(f"🔐 Migrating credentials from {json_file_path}...")

    if not os.path.exists(json_file_path):
        print(f"ℹ️  JSON file not found: {json_file_path}")
        return {}

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        credential_manager = get_credential_manager()
        migration_results = {}

        # Look for credentials section
        credentials = data.get("credentials", {})

        for key, cred_data in credentials.items():
            username = cred_data.get("username", "")
            password = cred_data.get("password", "")
            metadata = cred_data.get("metadata", {})

            if username and password:
                success = credential_manager.store_credential(key, username, password, metadata)
                migration_results[key] = success

                if success:
                    print(f"✅ Migrated credential: {key}")
                else:
                    print(f"❌ Failed to migrate credential: {key}")
            else:
                print(f"⚠️  Skipping incomplete credential: {key}")
                migration_results[key] = False

        return migration_results

    except Exception as e:
        print(f"❌ Error migrating from JSON file: {e}")
        return {}

def create_sample_credentials():
    """Create sample credentials for testing."""
    print("🔐 Creating sample credentials for testing...")

    try:
        credential_manager = get_credential_manager()

        # Sample email credential
        success1 = credential_manager.store_credential(
            key="sample_email",
            username="admin@company.com",
            password="sample_password_123",
            metadata={
                "purpose": "sample",
                "service": "email",
                "created": "2024-01-01"
            }
        )

        # Sample API credential
        success2 = credential_manager.store_credential(
            key="sample_api",
            username="api_user",
            password="api_secret_key_456",
            metadata={
                "purpose": "sample",
                "service": "api",
                "endpoint": "https://api.example.com"
            }
        )

        if success1 and success2:
            print("✅ Sample credentials created successfully")
            print("   - sample_email: admin@company.com")
            print("   - sample_api: api_user")
            return True
        else:
            print("❌ Failed to create some sample credentials")
            return False

    except Exception as e:
        print(f"❌ Error creating sample credentials: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 HET IT Control System - Credential Migration")
    print("=" * 50)

    # Migrate email credentials from config
    email_migrated = migrate_email_credentials()

    # Try to migrate from common config files
    config_files = [
        "config/credentials.json",
        "app/config/credentials.json",
        "credentials.json",
        ".env.credentials.json"
    ]

    json_migrations = {}
    for config_file in config_files:
        if os.path.exists(config_file):
            results = migrate_from_json_file(config_file)
            json_migrations.update(results)

    # Create sample credentials if none were migrated
    if not email_migrated and not json_migrations:
        print("\nℹ️  No existing credentials found. Creating sample credentials...")
        create_sample_credentials()

    print("\n✅ Credential migration completed!")
    print("\n📋 Next steps:")
    print("   1. Update your code to use get_credential_manager() instead of plaintext config")
    print("   2. Remove plaintext passwords from config files")
    print("   3. Test that your application still works with secure credentials")
    print("\n🔍 Example usage:")
    print("   from infrastructure.security import get_credential_manager")
    print("   cm = get_credential_manager()")
    print("   creds = cm.get_credential('email_smtp')")
    print("   print(creds['username'], creds['password'])")

if __name__ == "__main__":
    main()
<parameter name="filePath">d:\My App\infrastructure\security\migrate_credentials.py