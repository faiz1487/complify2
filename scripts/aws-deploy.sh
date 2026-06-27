#!/usr/bin/env bash
# Deploy to AWS: Terraform + Docker build/push to ECR + ECS.
# Requires: terraform, docker, aws cli
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT_DIR}/infrastructure/terraform"

cd "$TF_DIR"

echo "==> Step 1: Provision AWS infrastructure (VPC, RDS, Redis, S3, SQS, ECR, ALB, ECS)"
terraform init -input=false
terraform apply -auto-approve -var="app_ready=false"

REGION="$(terraform output -raw aws_region)"
PROJECT="$(terraform output -raw project_name)"
ALB_URL="$(terraform output -raw api_base_url)"
export AWS_REGION="$REGION"
export PROJECT_NAME="$PROJECT"
export IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "==> Step 2: Build Docker images locally and push to ECR"
"${ROOT_DIR}/scripts/docker-ecr-push.sh"

echo "==> Step 3: Start ECS Fargate services"
terraform apply -auto-approve -var="app_ready=true"

CLUSTER="${PROJECT}-cluster"
echo "==> Step 4: Rolling ECS deployment"
aws ecs update-service --cluster "$CLUSTER" --service upload-service --force-new-deployment --region "$REGION" >/dev/null
aws ecs update-service --cluster "$CLUSTER" --service data-processing-service --force-new-deployment --region "$REGION" >/dev/null
aws ecs update-service --cluster "$CLUSTER" --service retrieval-service --force-new-deployment --region "$REGION" >/dev/null

echo "    Waiting for ECS services to stabilize..."
aws ecs wait services-stable --cluster "$CLUSTER" --services upload-service data-processing-service retrieval-service --region "$REGION"

echo ""
echo "=============================================="
echo " Deployment complete"
echo "=============================================="
echo "API base URL: ${ALB_URL}"
echo ""
echo "Test upload:"
echo "  curl -X POST \"${ALB_URL}/api/upload\" -F \"file=@/path/to/file.pdf\""
echo ""
echo "Test search:"
echo "  curl \"${ALB_URL}/api/search/file.pdf\""
