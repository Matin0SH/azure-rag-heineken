# ===========================
# DATABRICKS VECTOR SEARCH OUTPUTS
# ===========================
# Values returned by this module

output "index_name" {
  description = "Full name of the vector search index"
  value       = databricks_vector_search_index.chunks_index.name
}

output "index_id" {
  description = "ID of the vector search index"
  value       = databricks_vector_search_index.chunks_index.id
}

output "endpoint_name" {
  description = "Vector search endpoint name"
  value       = databricks_vector_search_index.chunks_index.endpoint_name
}

output "index_status" {
  description = "Vector search index status"
  value       = databricks_vector_search_index.chunks_index.status
}

output "primary_key" {
  description = "Primary key column used for the index"
  value       = databricks_vector_search_index.chunks_index.primary_key
}
