output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.agent_service.uri
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker repository ID"
  value       = google_artifact_registry_repository.repo.id
}

output "bigquery_analytics_dataset" {
  description = "BigQuery dataset ID for telemetry and prompt-response logging"
  value       = google_bigquery_dataset.agent_logs.dataset_id
}
