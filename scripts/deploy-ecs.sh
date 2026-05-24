#!/usr/bin/env bash
# Rolling restart of ECS services after a new ECR image (run from AWS CloudShell).
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-document-services-cluster}"
INGESTION_SERVICE="${INGESTION_SERVICE:-ingestion-service}"
RETRIEVAL_SERVICE="${RETRIEVAL_SERVICE:-retrieval-service}"

echo "Forcing new deployment on ECS cluster: ${CLUSTER_NAME}"

aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$INGESTION_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION"

aws ecs update-service \
  --cluster "$CLUSTER_NAME" \
  --service "$RETRIEVAL_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION"

aws ecs wait services-stable \
  --cluster "$CLUSTER_NAME" \
  --services "$INGESTION_SERVICE" "$RETRIEVAL_SERVICE" \
  --region "$AWS_REGION"

echo "ECS services are stable."
