terraform {
  required_version = ">= 1.6.0"
  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.40"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-databricks-rag-dev"
    storage_account_name = "stdatabricksragstate"
    container_name       = "tfstate"
    key                  = "nextlevel/terraform.tfstate"
  }
}

provider "databricks" {
  host  = var.databricks_host
  token = var.databricks_token
}

# Base catalog/schema and volumes
module "databricks_foundation" {
  source      = "./modules/databricks_foundation"
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  environment  = var.environment

  providers = {
    databricks = databricks
  }
}

# Core tables
module "databricks_tables" {
  source       = "./modules/databricks_tables"
  catalog_name = var.catalog_name
  schema_name  = var.schema_name

  providers = {
    databricks = databricks
  }

  depends_on = [module.databricks_foundation]
}

# Vector index on chunks table
module "databricks_vector" {
  source                       = "./modules/databricks_vector"
  catalog_name                 = var.catalog_name
  schema_name                  = var.schema_name
  index_name                   = var.vector_index_name
  vector_search_endpoint_name  = var.vector_search_endpoint
  source_table_name            = "${var.catalog_name}.${var.schema_name}.chunks_embedded"

  providers = {
    databricks = databricks
  }

  depends_on = [module.databricks_tables]
}

# Databricks jobs for ingest_pipeline and summarization_pipeline
module "databricks_jobs" {
  source                  = "./modules/databricks_jobs"
  job_name                = var.job_name
  notebook_path           = var.notebook_path
  existing_cluster_id     = var.existing_cluster_id
  new_cluster_spark_version = var.new_cluster_spark_version
  new_cluster_node_type_id  = var.new_cluster_node_type_id
  new_cluster_num_workers   = var.new_cluster_num_workers
  max_retries             = var.max_retries
  retry_on_timeout        = var.retry_on_timeout
  timeout_seconds         = var.timeout_seconds
  catalog_name            = var.catalog_name
  schema_name             = var.schema_name
  embedding_model         = var.embedding_model
  vector_search_endpoint  = var.vector_search_endpoint
  vector_index_name       = var.vector_index_name

  # Summarization job variables
  job_name_prefix                = var.job_name_prefix
  summarization_notebook_path    = var.summarization_notebook_path
  timeout_seconds_summarization  = var.timeout_seconds_summarization
  llm_endpoint                   = var.llm_endpoint

  providers = {
    databricks = databricks
  }

  depends_on = [module.databricks_tables]
}
