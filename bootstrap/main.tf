# ===========================
# TERRAFORM BOOTSTRAP
# ===========================
# Purpose: Create the foundation infrastructure for Terraform state management
# This runs ONCE with local state, then we migrate to Azure backend

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.45"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.azure_subscription_id
  skip_provider_registration = true  # Skip auto-registration (university subscription)
}

provider "azuread" {}

# ===========================
# DATA SOURCES
# ===========================
# Get current Azure client configuration
data "azurerm_client_config" "current" {}

# ===========================
# RESOURCE GROUP
# ===========================
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.azure_region

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Purpose     = "Databricks RAG Application"
  }
}

# ===========================
# STORAGE ACCOUNT (for Terraform State)
# ===========================
resource "azurerm_storage_account" "tfstate" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"  # Locally Redundant Storage
  min_tls_version          = "TLS1_2"

  # Enable versioning for state file backups
  blob_properties {
    versioning_enabled = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Purpose     = "Terraform State Backend"
  }
}

# ===========================
# STORAGE CONTAINER (for state files)
# ===========================
resource "azurerm_storage_container" "tfstate" {
  name                  = "tfstate"
  storage_account_name  = azurerm_storage_account.tfstate.name
  container_access_type = "private"
}

# ===========================
# KEY VAULT (for secrets)
# ===========================
resource "azurerm_key_vault" "main" {
  name                       = var.key_vault_name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false  # Set to true for production

  # Allow current user to manage secrets
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Purge",
      "Recover"
    ]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Purpose     = "Secrets Management"
  }
}

# ===========================
# KEY VAULT SECRETS
# ===========================
# Store Databricks token
resource "azurerm_key_vault_secret" "databricks_token" {
  name         = "databricks-token"
  value        = var.databricks_token
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    Purpose = "Databricks Authentication"
  }
}

# Store Databricks host
resource "azurerm_key_vault_secret" "databricks_host" {
  name         = "databricks-host"
  value        = var.databricks_host
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    Purpose = "Databricks Configuration"
  }
}

# Store SQL Warehouse ID
resource "azurerm_key_vault_secret" "sql_warehouse_id" {
  name         = "databricks-warehouse-id"
  value        = var.sql_warehouse_id
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    Purpose = "Databricks SQL Configuration"
  }
}

# Store subscription ID
resource "azurerm_key_vault_secret" "subscription_id" {
  name         = "azure-subscription-id"
  value        = var.azure_subscription_id
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    Purpose = "Azure Configuration"
  }
}
