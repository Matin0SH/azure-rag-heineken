resource "databricks_job" "ingest_pipeline" {
  name                  = var.job_name
  max_concurrent_runs   = 1
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
    max_retries      = var.max_retries
    retry_on_timeout = var.retry_on_timeout

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

resource "databricks_job" "summarization_pipeline" {
  name                  = "${var.job_name_prefix}_summarization"
  max_concurrent_runs   = 3
  timeout_seconds       = var.timeout_seconds_summarization
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
    task_key = "summarization_pipeline"
    max_retries      = var.max_retries
    retry_on_timeout = var.retry_on_timeout

    notebook_task {
      notebook_path = var.summarization_notebook_path
      base_parameters = {
        pdf_id                = ""
        summary_type          = "technical"
        catalog               = var.catalog_name
        schema                = var.schema_name
        llm_endpoint          = var.llm_endpoint
        table_chunks          = "chunks_embedded"
        table_summaries       = "document_summaries"
      }
    }
  }
}

resource "databricks_job" "question_generation_pipeline" {
  name                  = "${var.job_name_prefix}_question_generation"
  max_concurrent_runs   = 3
  timeout_seconds       = var.timeout_seconds_question_generation
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
    task_key = "question_generation_pipeline"
    max_retries      = var.max_retries
    retry_on_timeout = var.retry_on_timeout

    notebook_task {
      notebook_path = var.question_generation_notebook_path
      base_parameters = {
        pdf_id                = ""
        catalog               = var.catalog_name
        schema                = var.schema_name
        llm_endpoint          = var.llm_endpoint
        table_chunks          = "chunks_embedded"
        table_questions       = "operator_questions"
      }
    }
  }
}
