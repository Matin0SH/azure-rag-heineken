# ===========================
# OUTPUTS
# ===========================

output "ingest_job_id" {
  description = "ID of the ingest pipeline job"
  value       = module.databricks_jobs.job_id
}

output "summarization_job_id" {
  description = "ID of the summarization pipeline job"
  value       = module.databricks_jobs.summarization_job_id
}

output "question_generation_job_id" {
  description = "ID of the question generation pipeline job"
  value       = module.databricks_jobs.question_generation_job_id
}

output "catalog_name" {
  description = "Unity Catalog name"
  value       = var.catalog_name
}

output "schema_name" {
  description = "Schema name"
  value       = var.schema_name
}
