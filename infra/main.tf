# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Service Account for NutriMeal Agent
resource "google_service_account" "agent_sa" {
  account_id   = "${var.app_name}-sa"
  display_name = "NutriMeal Agent Service Account"
}

# IAM Roles for Telemetry, Tracing, and Logging
resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Artifact Registry for Agent Docker Container
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.app_name
  description   = "Docker repository for ${var.app_name}"
  format        = "DOCKER"
}

# Cloud Run Service for NutriMeal Agent API & A2A Endpoint
resource "google_cloud_run_v2_service" "agent_service" {
  name     = var.app_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.repository_id}/agent:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "OTEL_TRACES_EXPORTER"
        value = "otlp"
      }
    }
  }
}

# Allow Unauthenticated Invocation for Web UI & A2A Route
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.agent_service.name
  location = google_cloud_run_v2_service.agent_service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# BigQuery Dataset for Observability & Agent Analytics
resource "google_bigquery_dataset" "agent_logs" {
  dataset_id                  = "${replace(var.app_name, "-", "_")}_analytics"
  friendly_name               = "NutriMeal Agent Analytics & Telemetry"
  description                 = "BigQuery dataset storing prompt-response logs and agent telemetry"
  location                    = var.region
  default_table_expiration_ms = 7776000000 # 90 days
}
