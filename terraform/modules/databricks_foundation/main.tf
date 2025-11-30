# ===========================
# DATABRICKS FOUNDATION MODULE
# ===========================
# Purpose: Create Unity Catalog schema and volumes
# This is the foundation that all other resources depend on

# ===========================
# UNITY CATALOG SCHEMA
# ===========================
resource "databricks_schema" "main" {
  catalog_name = var.catalog_name
  name         = var.schema_name
  comment      = "Schema for Databricks RAG application - managed by Terraform"

  properties = {
    environment = var.environment
    managed_by  = "terraform"
    project     = "databricks-rag"
  }
}

# ===========================
# VOLUME: raw_pdfs
# ===========================
# Stores uploaded PDF files
resource "databricks_volume" "raw_pdfs" {
  catalog_name = var.catalog_name
  schema_name  = databricks_schema.main.name
  name         = "raw_pdfs"
  volume_type  = "MANAGED"
  comment      = "Storage for uploaded PDF documents"

  # Ensure schema exists first
  depends_on = [databricks_schema.main]
}

# ===========================
# VOLUME: screenshots
# ===========================
# Stores page screenshot images from PDF parsing
resource "databricks_volume" "screenshots" {
  catalog_name = var.catalog_name
  schema_name  = databricks_schema.main.name
  name         = "screenshots"
  volume_type  = "MANAGED"
  comment      = "Storage for PDF page screenshot images"

  # Ensure schema exists first
  depends_on = [databricks_schema.main]
}
