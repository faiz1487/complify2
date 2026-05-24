resource "aws_cloudwatch_log_group" "ingestion" {
  name              = "/ecs/${var.project_name}/ingestion-service"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "retrieval" {
  name              = "/ecs/${var.project_name}/retrieval-service"
  retention_in_days = 30
}
