"""
Setup script to create Databricks secret scope and add secrets.

This script will:
1. Create a secret scope called 'nextlevel-api'
2. Add DATABRICKS_TOKEN secret
3. Add API_KEY secret

Run this ONCE before deploying the app.
"""
from databricks.sdk import WorkspaceClient
import os

# Initialize Databricks client (reads from .env or environment)
w = WorkspaceClient(
    host=os.getenv("DATABRICKS_HOST"),
    token=os.getenv("DATABRICKS_TOKEN")
)

if not w.config.host or not w.config.token:
    raise ValueError("DATABRICKS_HOST and DATABRICKS_TOKEN must be set in environment or .env file")

print("=" * 80)
print("SETTING UP DATABRICKS SECRETS FOR NEXTLEVEL-API")
print("=" * 80)

# Step 1: Create secret scope
scope_name = "nextlevel-api"

try:
    print(f"\n[1/3] Creating secret scope: {scope_name}")
    w.secrets.create_scope(scope=scope_name)
    print(f"OK: Secret scope '{scope_name}' created successfully")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"OK: Secret scope '{scope_name}' already exists (skipping)")
    else:
        print(f"ERROR: Error creating scope: {e}")
        raise

# Step 2: Add DATABRICKS_TOKEN secret
try:
    print(f"\n[2/3] Adding DATABRICKS_TOKEN secret")
    databricks_token = os.getenv("DATABRICKS_TOKEN")
    if not databricks_token:
        raise ValueError("DATABRICKS_TOKEN environment variable not set")

    w.secrets.put_secret(
        scope=scope_name,
        key="databricks-token",
        string_value=databricks_token
    )
    print(f"OK: Added 'databricks-token' secret")
except Exception as e:
    print(f"ERROR: Error adding databricks-token: {e}")
    raise

# Step 3: Add API_KEY secret
try:
    print(f"\n[3/3] Adding API_KEY secret")
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set")

    w.secrets.put_secret(
        scope=scope_name,
        key="api-key",
        string_value=api_key
    )
    print(f"OK: Added 'api-key' secret")
except Exception as e:
    print(f"ERROR: Error adding api-key: {e}")
    raise

# Verify secrets are accessible
print(f"\n[Verification] Listing secrets in scope '{scope_name}':")
try:
    secrets = w.secrets.list_secrets(scope=scope_name)
    for secret in secrets:
        print(f"  - {secret.key}")
except Exception as e:
    print(f"ERROR: Error listing secrets: {e}")

print("\n" + "=" * 80)
print("OK: SECRETS SETUP COMPLETE")
print("=" * 80)
print(f"\nSecret scope: {scope_name}")
print("Secrets added:")
print("  1. databricks-token")
print("  2. api-key")
print("\nThese secrets will be automatically injected into your Databricks App")
print("via the app.yaml configuration.")
print("=" * 80)
