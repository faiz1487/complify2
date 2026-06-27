resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

locals {
  common_environment = [
    { name = "DB_HOST", value = aws_db_instance.postgres.address },
    { name = "DB_PORT", value = "5432" },
    { name = "DB_NAME", value = var.db_name },
    { name = "DB_USER", value = var.db_username },
    { name = "REDIS_HOST", value = aws_elasticache_replication_group.redis.primary_endpoint_address },
    { name = "REDIS_PORT", value = "6379" },
    { name = "S3_BUCKET", value = aws_s3_bucket.documents.bucket },
    { name = "AWS_REGION", value = var.aws_region },
    { name = "SQS_QUEUE_URL", value = aws_sqs_queue.processing.url },
    { name = "S3_PREFIX_RAW", value = local.s3_prefixes.upload },
    { name = "S3_PREFIX_PROCESSING", value = local.s3_prefixes.processing },
    { name = "S3_PREFIX_PROCESSED", value = local.s3_prefixes.processed },
    { name = "S3_PREFIX_FAILED", value = local.s3_prefixes.failed },
    { name = "S3_PREFIX_ARCHIVED", value = local.s3_prefixes.archived },
    { name = "OPENAI_API_KEY", value = var.openai_api_key },
  ]

  common_secrets = [
    {
      name      = "DB_PASSWORD"
      valueFrom = aws_secretsmanager_secret.db_password.arn
    },
  ]
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/db-password"
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_ecs_task_definition" "upload" {
  family                   = "${var.project_name}-upload"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "3072"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "upload-service"
      image     = "${aws_ecr_repository.upload.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 4000
          protocol      = "tcp"
        }
      ]
      environment = local.common_environment
      secrets     = local.common_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.upload.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_task_definition" "processing" {
  family                   = "${var.project_name}-processing"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "data-processing-service"
      image     = "${aws_ecr_repository.processing.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 4003
          protocol      = "tcp"
        }
      ]
      environment = local.common_environment
      secrets     = local.common_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.processing.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:4003/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 90
      }
    }
  ])
}

resource "aws_ecs_task_definition" "retrieval" {
  family                   = "${var.project_name}-retrieval"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "retrieval-service"
      image     = "${aws_ecr_repository.retrieval.repository_url}:${var.image_tag}"
      essential = true
      portMappings = [
        {
          containerPort = 4002
          protocol      = "tcp"
        }
      ]
      environment = local.common_environment
      secrets     = local.common_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.retrieval.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:4002/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_service" "upload" {
  name            = "upload-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.upload.arn
  desired_count   = var.app_ready ? var.upload_desired_count : 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.upload.arn
    container_name   = "upload-service"
    container_port   = 4000
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "processing" {
  name            = "data-processing-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.processing.arn
  desired_count   = var.app_ready ? var.processing_desired_count : 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_processing.id]
    assign_public_ip = false
  }
}

resource "aws_ecs_service" "retrieval" {
  name            = "retrieval-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.retrieval.arn
  desired_count   = var.app_ready ? var.retrieval_desired_count : 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.retrieval.arn
    container_name   = "retrieval-service"
    container_port   = 4002
  }

  depends_on = [aws_lb_listener.http]
}
