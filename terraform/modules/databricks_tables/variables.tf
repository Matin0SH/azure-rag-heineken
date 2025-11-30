# ===========================
# DATABRICKS TABLES VARIABLES
# ===========================
# Input variables for the databricks_tables module

variable "catalog_name" {
  description = "Unity Catalog name"
  type        = string
}

variable "schema_name" {
  description = "Schema name where tables will be created"
  type        = string
}
