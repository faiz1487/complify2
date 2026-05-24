# ECS Service Configuration

## Cluster

- Name: `document-services-cluster` (from Terraform `aws_ecs_cluster.main`)

## Services

| Service            | Task CPU | Task Memory | Container Port | Desired Count | Subnets        |
|--------------------|----------|-------------|----------------|---------------|----------------|
| ingestion-service  | 1024     | 3072 MB     | 4001           | 2 (default)   | Private subnets |
| retrieval-service  | 1024     | 2048 MB     | 4002           | 2 (default)   | Private subnets |

## Load Balancer

- Type: Application Load Balancer (public subnets)
- Listener: HTTP :80
- Rules:
  - Priority 100: `/api/upload`, `/api/upload/*` → ingestion target group (port 4001)
  - Priority 200: `/api/search`, `/api/search/*` → retrieval target group (port 4002)

## Networking

- ECS tasks: `assign_public_ip = false` in private subnets
- Outbound via NAT Gateway (Multi-AZ)
- RDS: database subnets, Multi-AZ
- Redis: ElastiCache in private subnets, Multi-AZ with automatic failover

## IAM

- **Execution role**: ECR pull, CloudWatch Logs, Secrets Manager (`DB_PASSWORD`)
- **Task role**: S3 object read/write on document bucket

## Health Checks

- ALB target group: `GET /health` every 30s
- ECS container health check: same `/health` endpoint on container port
