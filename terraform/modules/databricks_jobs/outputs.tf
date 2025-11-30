output "job_id" {
  description = "ID of the ingest pipeline job"
  value       = databricks_job.ingest_pipeline.id
}
