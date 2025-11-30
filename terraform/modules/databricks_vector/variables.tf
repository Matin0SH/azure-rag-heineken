# ===========================
# DATABRICKS VECTOR SEARCH VARIABLES
# ===========================
# Input variables for the databricks_vector module

variable "catalog_name" {
  description = "Unity Catalog name"
  type        = string
}

variable "schema_name" {
  description = "Schema name where index will be created"
  type        = string
}

variable "index_name" {
  description = "Name of the vector search index"
  type        = string
  default     = "chunks_embedded_index"
}

variable "vector_search_endpoint_name" {
  description = "Name of the existing vector search endpoint"
  type        = string
}

variable "source_table_name" {
  description = "Full name of the source table (catalog.schema.table)"
  type        = string
}
