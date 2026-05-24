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

# -----------------------------
# Public Subnet CIDRs
# -----------------------------
variable "public_subnet_cidrs" {
  type = list(string)

  default = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]
}

# -----------------------------
# Private Subnet CIDRs
# -----------------------------
variable "private_subnet_cidrs" {
  type = list(string)

  default = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]
}

# -----------------------------
# Database Subnet CIDRs
# -----------------------------
variable "database_subnet_cidrs" {
  type = list(string)

  default = [
    "10.0.21.0/24",
    "10.0.22.0/24"
  ]
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

variable "ingestion_desired_count" {
  type    = number
  default = 1
}

variable "retrieval_desired_count" {
  type    = number
  default = 1
}

variable "openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}