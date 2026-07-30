variable "project_id" {
  description = "GCP Project ID"
  type        = string
  default     = "ssavardekar-agent-sandbox"
}

variable "region" {
  description = "GCP Region for deployment"
  type        = string
  default     = "us-east1"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "nutri-meal-agent"
}
