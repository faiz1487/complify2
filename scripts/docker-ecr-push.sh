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

REGISTRY="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
UPLOAD_REPO="${REGISTRY}/${PROJECT_NAME}/upload-service"
PROCESSING_REPO="${REGISTRY}/${PROJECT_NAME}/data-processing-service"
RETRIEVAL_REPO="${REGISTRY}/${PROJECT_NAME}/retrieval-service"

echo "==> Logging in to ECR (${AWS_REGION})"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$REGISTRY"

echo "==> Building upload-service"
docker build -f upload-service/Dockerfile -t "${UPLOAD_REPO}:${IMAGE_TAG}" .

echo "==> Building data-processing-service"
docker build -f data-processing-service/Dockerfile -t "${PROCESSING_REPO}:${IMAGE_TAG}" .

echo "==> Building retrieval-service"
docker build -f retrieval-service/Dockerfile -t "${RETRIEVAL_REPO}:${IMAGE_TAG}" .

echo "==> Pushing images"
docker push "${UPLOAD_REPO}:${IMAGE_TAG}"
docker push "${PROCESSING_REPO}:${IMAGE_TAG}"
docker push "${RETRIEVAL_REPO}:${IMAGE_TAG}"

echo ""
echo "Pushed:"
echo "  ${UPLOAD_REPO}:${IMAGE_TAG}"
echo "  ${PROCESSING_REPO}:${IMAGE_TAG}"
echo "  ${RETRIEVAL_REPO}:${IMAGE_TAG}"
