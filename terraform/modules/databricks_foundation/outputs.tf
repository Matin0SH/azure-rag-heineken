# ===========================
# DATABRICKS FOUNDATION OUTPUTS
# ===========================
# Values returned by this module for use by other modules

output "schema_id" {
  description = "Full schema identifier (catalog.schema)"
  value       = databricks_schema.main.id
}

output "schema_name" {
  description = "Schema name"
  value       = databricks_schema.main.name
}

output "catalog_name" {
  description = "Catalog name"
  value       = databricks_schema.main.catalog_name
}

output "raw_pdfs_volume_path" {
  description = "Full path to raw_pdfs volume"
  value       = databricks_volume.raw_pdfs.volume_path
}

output "screenshots_volume_path" {
  description = "Full path to screenshots volume"
  value       = databricks_volume.screenshots.volume_path
}

output "raw_pdfs_volume_id" {
  description = "ID of raw_pdfs volume"
  value       = databricks_volume.raw_pdfs.id
}

output "screenshots_volume_id" {
  description = "ID of screenshots volume"
  value       = databricks_volume.screenshots.id
}

# Composite output for easy reference
output "volume_paths" {
  description = "Map of volume names to their paths"
  value = {
    raw_pdfs    = databricks_volume.raw_pdfs.volume_path
    screenshots = databricks_volume.screenshots.volume_path
  }
}
