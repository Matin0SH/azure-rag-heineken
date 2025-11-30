# ===========================
# DATABRICKS TABLES OUTPUTS
# ===========================
# Values returned by this module

output "pdf_registery_id" {
  description = "ID of pdf_registery table"
  value       = databricks_sql_table.pdf_registery.id
}

output "chunks_embedded_id" {
  description = "ID of chunks_embedded table (used for vector index)"
  value       = databricks_sql_table.chunks_embedded.id
}

output "page_screenshots_id" {
  description = "ID of page_screenshots table"
  value       = databricks_sql_table.page_screenshots.id
}

output "document_summaries_id" {
  description = "ID of document_summaries table"
  value       = databricks_sql_table.document_summaries.id
}

output "operator_questions_id" {
  description = "ID of operator_questions table"
  value       = databricks_sql_table.operator_questions.id
}

# Full table names (for reference in SQL queries)
output "table_names" {
  description = "Map of all table names"
  value = {
    pdf_registery        = "${var.catalog_name}.${var.schema_name}.pdf_registery"
    chunks_embedded     = "${var.catalog_name}.${var.schema_name}.chunks_embedded"
    page_screenshots    = "${var.catalog_name}.${var.schema_name}.page_screenshots"
    document_summaries  = "${var.catalog_name}.${var.schema_name}.document_summaries"
    operator_questions  = "${var.catalog_name}.${var.schema_name}.operator_questions"
  }
}

# Chunks table details (needed for vector search index)
output "chunks_table_full_name" {
  description = "Full name of chunks_embedded table for vector index"
  value       = "${var.catalog_name}.${var.schema_name}.chunks_embedded"
}
