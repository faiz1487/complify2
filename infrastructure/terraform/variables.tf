variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "document-services"
}

variable "environment" {
  type    = string
  default = "prod"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "db_name" {
  type    = string
  default = "documents"
}

variable "db_username" {
  type    = string
  default = "docadmin"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Docker image tag (built locally and pushed to ECR)"
}

variable "app_ready" {
  type        = bool
  default     = false
  description = "Set true after Docker images are pushed to ECR (deploy script does this)"
}

variable "upload_desired_count" {
  type    = number
  default = 2
}

variable "processing_desired_count" {
  type    = number
  default = 2
}

variable "retrieval_desired_count" {
  type    = number
  default = 2
}

variable "autoscaling_min_capacity" {
  type    = number
  default = 1
}

variable "autoscaling_max_capacity" {
  type    = number
  default = 6
}

variable "autoscaling_target_cpu" {
  type    = number
  default = 70
}

variable "openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
