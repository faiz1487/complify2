#!/usr/bin/env bash
# Build Docker images locally and push to AWS ECR.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-document-services}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

if [ -z "${ACCOUNT_ID:-}" ]; then
  ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
fi

INGESTION_REPO="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}/ingestion-service"
RETRIEVAL_REPO="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}/retrieval-service"

echo "==> Logging in to ECR (${AWS_REGION})"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Building ingestion-service"
docker build -f ingestion-service/Dockerfile -t "${INGESTION_REPO}:${IMAGE_TAG}" .

echo "==> Building retrieval-service"
docker build -f retrieval-service/Dockerfile -t "${RETRIEVAL_REPO}:${IMAGE_TAG}" .

echo "==> Pushing images"
docker push "${INGESTION_REPO}:${IMAGE_TAG}"
docker push "${RETRIEVAL_REPO}:${IMAGE_TAG}"

echo ""
echo "Pushed:"
echo "  ${INGESTION_REPO}:${IMAGE_TAG}"
echo "  ${RETRIEVAL_REPO}:${IMAGE_TAG}"
