# ===========================
# DATABRICKS FOUNDATION VARIABLES
# ===========================
# Input variables for the databricks_foundation module

variable "catalog_name" {
  description = "Unity Catalog name (existing catalog to use)"
  type        = string

  validation {
    condition     = length(var.catalog_name) > 0
    error_message = "Catalog name cannot be empty."
  }
}

variable "schema_name" {
  description = "Schema name to create in the catalog"
  type        = string

  validation {
    condition     = length(var.schema_name) > 0
    error_message = "Schema name cannot be empty."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}
