# ===========================
# BOOTSTRAP VARIABLES
# ===========================
# Input variables for bootstrap Terraform configuration

# ===========================
# Azure Configuration
# ===========================
variable "azure_subscription_id" {
  description = "Azure Subscription ID"
  type        = string
  sensitive   = true
}

variable "azure_region" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ===========================
# Resource Naming
# ===========================
variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "databricks-rag"
}

variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
}

variable "storage_account_name" {
  description = "Name of the Storage Account for Terraform state (3-24 chars, lowercase, numbers only)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9]{3,24}$", var.storage_account_name))
    error_message = "Storage account name must be 3-24 characters, lowercase letters and numbers only."
  }
}

variable "key_vault_name" {
  description = "Name of the Key Vault (3-24 chars, alphanumeric and hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9-]{1,22}[a-zA-Z0-9]$", var.key_vault_name))
    error_message = "Key Vault name must be 3-24 characters, start with letter, alphanumeric and hyphens only."
  }
}

# ===========================
# Databricks Configuration
# ===========================
variable "databricks_host" {
  description = "Databricks workspace URL"
  type        = string
}

variable "databricks_token" {
  description = "Databricks Personal Access Token"
  type        = string
  sensitive   = true
}

variable "sql_warehouse_id" {
  description = "Databricks SQL Warehouse ID"
  type        = string
}
