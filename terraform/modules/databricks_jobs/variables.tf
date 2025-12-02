variable "job_name" {
  description = "Name of the Databricks job"
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
  description = "Spark version for the new cluster (if existing_cluster_id not set)"
  type        = string
  default     = "13.3.x-scala2.12"
}

variable "new_cluster_node_type_id" {
  description = "Node type for the new cluster (if existing_cluster_id not set)"
  type        = string
  default     = "Standard_DS3_v2"
}

variable "new_cluster_num_workers" {
  description = "Worker count for the new cluster (if existing_cluster_id not set)"
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

variable "catalog_name" {
  description = "Catalog name"
  type        = string
}

variable "schema_name" {
  description = "Schema name"
  type        = string
}

variable "embedding_model" {
  description = "Embedding model name for the job parameter"
  type        = string
  default     = "databricks-gte-large-en"
}

variable "vector_search_endpoint" {
  description = "Vector search endpoint name"
  type        = string
}

variable "vector_index_name" {
  description = "Vector search index name"
  type        = string
  default     = "chunks_embedded_index"
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

# Question generation job variables
variable "question_generation_notebook_path" {
  description = "Workspace path to the question_generation_pipeline notebook/script"
  type        = string
}

variable "timeout_seconds_question_generation" {
  description = "Timeout for question generation job"
  type        = number
  default     = 3600
}
