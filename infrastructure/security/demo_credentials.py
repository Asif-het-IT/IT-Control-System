# infrastructure/security/demo_credentials.py
"""
Demo script showing how to use the Windows Credential Manager for secure credential storage.
This demonstrates the enterprise-ready credential management system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from infrastructure.security.credential_manager import get_credential_manager

def demo_basic_usage():
    """Demonstrate basic credential manager usage."""
    print("🔐 Windows Credential Manager Demo")
    print("=" * 40)

    cm = get_credential_manager()

    # Store a credential
    print("\n📝 Storing a credential...")
    success = cm.store_credential(
        key="demo_email",
        username="user@company.com",
        password="secure_password_123",
        metadata={
            "service": "email",
            "environment": "production",
            "last_updated": "2024-01-01"
        }
    )

    if success:
        print("✅ Credential stored successfully")
    else:
        print("❌ Failed to store credential")
        return

    # Retrieve the credential
    print("\n📖 Retrieving the credential...")
    credential = cm.get_credential("demo_email")

    if credential:
        print("✅ Credential retrieved successfully")
        print(f"   Username: {credential['username']}")
        print(f"   Password: {credential['password']}")
        print(f"   Metadata: {credential['metadata']}")
    else:
        print("❌ Failed to retrieve credential")

    # Check if credential exists
    print(f"\n🔍 Credential exists: {cm.credential_exists('demo_email')}")

    # Get credential info (without password)
    print("\nℹ️  Getting credential info (no password)...")
    info = cm.get_credential_info("demo_email")
    if info:
        print(f"   Username: {info['username']}")
        print(f"   Metadata: {info['metadata']}")

    # Update the credential
    print("\n✏️  Updating the credential...")
    update_success = cm.update_credential(
        key="demo_email",
        password="new_secure_password_456",
        metadata={
            "service": "email",
            "environment": "production",
            "last_updated": "2024-01-15"
        }
    )

    if update_success:
        print("✅ Credential updated successfully")
    else:
        print("❌ Failed to update credential")

    # Verify the update
    updated_cred = cm.get_credential("demo_email")
    if updated_cred:
        print(f"   New password: {updated_cred['password']}")
        print(f"   Updated metadata: {updated_cred['metadata']}")

def demo_enterprise_usage():
    """Demonstrate enterprise usage patterns."""
    print("\n🏢 Enterprise Usage Patterns")
    print("=" * 40)

    cm = get_credential_manager()

    # Store multiple service credentials
    services = [
        {
            "key": "prod_database",
            "username": "db_admin",
            "password": "db_secure_pass_789",
            "metadata": {
                "service": "postgresql",
                "environment": "production",
                "host": "prod-db.company.com",
                "database": "het_control"
            }
        },
        {
            "key": "smtp_relay",
            "username": "noreply@company.com",
            "password": "smtp_app_password",
            "metadata": {
                "service": "email",
                "provider": "gmail",
                "host": "smtp.gmail.com",
                "port": 587
            }
        },
        {
            "key": "api_gateway",
            "username": "het_control_service",
            "password": "api_gateway_secret",
            "metadata": {
                "service": "api",
                "provider": "internal",
                "endpoints": ["auth", "jobs", "monitoring"]
            }
        }
    ]

    print("\n📝 Storing enterprise credentials...")
    for service in services:
        success = cm.store_credential(**service)
        status = "✅" if success else "❌"
        print(f"   {status} {service['key']}")

    # Demonstrate retrieval for application use
    print("\n🔧 Retrieving credentials for application use...")

    # Simulate getting database credentials
    db_creds = cm.get_credential("prod_database")
    if db_creds:
        print("Database connection:")
        print(f"  Host: {db_creds['metadata']['host']}")
        print(f"  User: {db_creds['username']}")
        print("  Password: [HIDDEN]")  # Never log passwords
        print(f"  Database: {db_creds['metadata']['database']}")

    # Simulate getting email credentials
    email_creds = cm.get_credential("smtp_relay")
    if email_creds:
        print("\nEmail configuration:")
        print(f"  SMTP Host: {email_creds['metadata']['host']}")
        print(f"  Username: {email_creds['username']}")
        print("  Password: [HIDDEN]")  # Never log passwords
        print(f"  Port: {email_creds['metadata']['port']}")

def demo_error_handling():
    """Demonstrate error handling."""
    print("\n⚠️  Error Handling Demo")
    print("=" * 40)

    cm = get_credential_manager()

    # Try to get non-existent credential
    print("\n🔍 Trying to get non-existent credential...")
    result = cm.get_credential("non_existent_key")
    print(f"   Result: {result}")  # Should be None

    # Try to store invalid credential
    print("\n📝 Trying to store invalid credential...")
    success = cm.store_credential("", "user", "pass")  # Empty key
    print(f"   Success: {success}")  # Should be False

    # Try to delete non-existent credential
    print("\n🗑️  Trying to delete non-existent credential...")
    deleted = cm.delete_credential("non_existent_key")
    print(f"   Deleted: {deleted}")  # Should be False

def cleanup_demo():
    """Clean up demo credentials."""
    print("\n🧹 Cleaning up demo credentials...")
    cm = get_credential_manager()

    demo_keys = ["demo_email", "prod_database", "smtp_relay", "api_gateway"]

    for key in demo_keys:
        success = cm.delete_credential(key)
        status = "✅" if success else "ℹ️ "
        print(f"   {status} {key}")

def main():
    """Run the credential manager demo."""
    try:
        demo_basic_usage()
        demo_enterprise_usage()
        demo_error_handling()

        print("\n🎉 Demo completed successfully!")
        print("\n💡 The Windows Credential Manager is now ready for production use.")
        print("   Your credentials are securely stored and protected by Windows.")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("   Make sure Windows Credential Manager is available on your system.")

    finally:
        # Always clean up demo data
        cleanup_demo()

if __name__ == "__main__":
    main()
<parameter name="filePath">d:\My App\infrastructure\security\demo_credentials.py