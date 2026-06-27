output "alb_dns_name" {
  description = "Public ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "s3_prefixes" {
  description = "S3 lifecycle folder prefixes"
  value       = local.s3_prefixes
}

output "s3_bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "sqs_processing_queue_url" {
  value = aws_sqs_queue.processing.url
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "ecr_upload_repository_url" {
  value = aws_ecr_repository.upload.repository_url
}

output "ecr_processing_repository_url" {
  value = aws_ecr_repository.processing.repository_url
}

output "ecr_retrieval_repository_url" {
  value = aws_ecr_repository.retrieval.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cloudwatch_log_groups" {
  value = [
    aws_cloudwatch_log_group.upload.name,
    aws_cloudwatch_log_group.processing.name,
    aws_cloudwatch_log_group.retrieval.name,
  ]
}

output "aws_region" {
  value = var.aws_region
}

output "project_name" {
  value = var.project_name
}

output "api_base_url" {
  description = "Public API base URL (ALB)"
  value       = "http://${aws_lb.main.dns_name}"
}
