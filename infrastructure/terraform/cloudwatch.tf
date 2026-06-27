resource "aws_cloudwatch_log_group" "upload" {
  name              = "/ecs/${var.project_name}/upload-service"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "processing" {
  name              = "/ecs/${var.project_name}/data-processing-service"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "retrieval" {
  name              = "/ecs/${var.project_name}/retrieval-service"
  retention_in_days = 30
}
