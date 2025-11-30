# ===========================
# DATABRICKS VECTOR SEARCH MODULE
# ===========================
# Purpose: Create vector search index for RAG retrieval
# Uses existing vector search endpoint

# ===========================
# DATA SOURCE: Existing Vector Search Endpoint
# ===========================
# Reference the pre-existing vector search endpoint (not managed by Terraform)
data "databricks_vector_search_endpoint" "existing" {
  name = var.vector_search_endpoint_name
}

# ===========================
# VECTOR SEARCH INDEX
# ===========================
# Creates a vector search index on chunks_embedded table
resource "databricks_vector_search_index" "chunks_index" {
  name             = "${var.catalog_name}.${var.schema_name}.${var.index_name}"
  endpoint_name    = data.databricks_vector_search_endpoint.existing.name
  primary_key      = "chunk_id"
  index_type       = "DELTA_SYNC"

  # Source table configuration
  delta_sync_index_spec {
    source_table       = var.source_table_name
    embedding_source_columns {
      name               = "embedding"
      embedding_model_endpoint_name = null  # Embeddings already computed, not using an endpoint
    }
  }

  # Note: Index will auto-sync when source table updates (CONTINUOUS mode)
}
