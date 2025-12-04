variable "databricks_host" {
  description = "Databricks workspace URL"
  type        = string
}

variable "databricks_workspace_url" {
  description = "Databricks workspace URL (alternative name)"
  type        = string
}

variable "databricks_workspace_id" {
  description = "Databricks workspace ID"
  type        = string
}

variable "databricks_token" {
  description = "Databricks personal access token"
  type        = string
  sensitive   = true
}

variable "github_repo_url" {
  description = "GitHub repository URL"
  type        = string
}

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  sensitive   = true
}

variable "azure_region" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "databricks-rag"
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "storage_account_name" {
  description = "Storage account name"
  type        = string
}

variable "key_vault_name" {
  description = "Key vault name"
  type        = string
}

variable "container_registry_name" {
  description = "Container registry name"
  type        = string
}

variable "app_service_name" {
  description = "App service name"
  type        = string
}

variable "app_service_tier" {
  description = "App service tier"
  type        = string
  default     = "B1"
}

variable "catalog_name" {
  description = "Unity Catalog name"
  type        = string
}

variable "schema_name" {
  description = "Schema name"
  type        = string
}

variable "environment" {
  description = "Environment label (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "vector_search_endpoint" {
  description = "Vector search endpoint name"
  type        = string
}

variable "vector_index_name" {
  description = "Vector index name"
  type        = string
  default     = "chunks_embedded_index"
}

variable "embedding_model" {
  description = "Embedding model name for ingest job parameter"
  type        = string
  default     = "databricks-gte-large-en"
}

variable "job_name" {
  description = "Name of the ingest pipeline job"
  type        = string
  default     = "ingest_pipeline"
}

variable "notebook_path" {
  description = "Workspace path to the ingest_pipeline notebook/script"
  type        = string
}

variable "existing_cluster_id" {
  description = "Optional existing cluster ID to run the job on"
  type        = string
  default     = ""
}

variable "new_cluster_spark_version" {
  description = "Spark version for new cluster if existing_cluster_id not set"
  type        = string
  default     = "13.3.x-scala2.12"
}

variable "new_cluster_node_type_id" {
  description = "Node type for new cluster if existing_cluster_id not set"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "new_cluster_num_workers" {
  description = "Worker count for new cluster if existing_cluster_id not set"
  type        = number
  default     = 1
}

variable "max_retries" {
  description = "Job max retries"
  type        = number
  default     = 1
}

variable "retry_on_timeout" {
  description = "Retry job on timeout"
  type        = bool
  default     = true
}

variable "timeout_seconds" {
  description = "Optional job timeout"
  type        = number
  default     = 0
}

# Summarization job variables
variable "job_name_prefix" {
  description = "Prefix for job names"
  type        = string
  default     = "nextlevel_rag"
}

variable "summarization_notebook_path" {
  description = "Workspace path to the summarization_pipeline notebook/script"
  type        = string
}

variable "timeout_seconds_summarization" {
  description = "Timeout for summarization job (longer than ingest)"
  type        = number
  default     = 3600
}

variable "llm_endpoint" {
  description = "LLM endpoint for summarization"
  type        = string
  default     = "databricks-llama-4-maverick"
}

variable "question_generation_notebook_path" {
  description = "Workspace path to the question_generation_pipeline notebook/script"
  type        = string
}

variable "timeout_seconds_question_generation" {
  description = "Timeout for question generation job"
  type        = number
  default     = 3600
}
