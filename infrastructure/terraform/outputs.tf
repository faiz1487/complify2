output "alb_dns_name" {
  description = "Public ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.documents.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.endpoint
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "ecr_ingestion_repository_url" {
  value = aws_ecr_repository.ingestion.repository_url
}

output "ecr_retrieval_repository_url" {
  value = aws_ecr_repository.retrieval.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "cloudwatch_log_groups" {
  value = [
    aws_cloudwatch_log_group.ingestion.name,
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
