resource "databricks_job" "ingest_pipeline" {
  name                  = var.job_name
  max_concurrent_runs   = 1
  max_retries           = var.max_retries
  retry_on_timeout      = var.retry_on_timeout
  timeout_seconds       = var.timeout_seconds
  existing_cluster_id   = var.existing_cluster_id != "" ? var.existing_cluster_id : null

  dynamic "new_cluster" {
    for_each = var.existing_cluster_id == "" ? [1] : []
    content {
      spark_version = var.new_cluster_spark_version
      node_type_id  = var.new_cluster_node_type_id
      num_workers   = var.new_cluster_num_workers
    }
  }

  task {
    task_key = "ingest_pipeline"

    notebook_task {
      notebook_path = var.notebook_path
      base_parameters = {
        pdf_name              = ""
        pdf_id                = ""
        catalog               = var.catalog_name
        schema                = var.schema_name
        embedding_model       = var.embedding_model
        volume_raw_pdfs       = "raw_pdfs"
        volume_screenshots    = "screenshots"
        vector_search_endpoint = var.vector_search_endpoint
        vector_index_name      = var.vector_index_name
        table_chunks          = "chunks_embedded"
        table_registery       = "pdf_registery"
        table_screenshots     = "page_screenshots"
      }
    }
  }
}
