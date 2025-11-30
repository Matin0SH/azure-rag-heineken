# ===========================
# DATABRICKS VECTOR SEARCH MODULE
# ===========================
# Purpose: Create vector search index for RAG retrieval
# Uses existing vector search endpoint

# ===========================
# ===========================
# VECTOR SEARCH INDEX
# ===========================
# Creates a vector search index on chunks_embedded table
resource "databricks_vector_search_index" "chunks_index" {
  name          = "${var.catalog_name}.${var.schema_name}.${var.index_name}"
  endpoint_name = var.vector_search_endpoint_name
  primary_key   = "chunk_id"
  index_type    = "DELTA_SYNC"

  # Source table configuration
  delta_sync_index_spec {
    source_table = var.source_table_name
    embedding_vector_columns {
      name = "embedding"
    }
  }

  # Note: Index will auto-sync when source table updates (CONTINUOUS mode)
}
