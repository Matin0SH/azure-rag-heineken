output "job_id" {
  description = "ID of the ingest pipeline job"
  value       = databricks_job.ingest_pipeline.id
}

output "summarization_job_id" {
  description = "ID of the summarization pipeline job"
  value       = databricks_job.summarization_pipeline.id
}

output "question_generation_job_id" {
  description = "ID of the question generation pipeline job"
  value       = databricks_job.question_generation_pipeline.id
}
