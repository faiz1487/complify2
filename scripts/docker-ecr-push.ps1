# Build Docker images locally and push to AWS ECR (Windows PowerShell).
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RootDir

$AwsRegion = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
$ProjectName = if ($env:PROJECT_NAME) { $env:PROJECT_NAME } else { "document-services" }
$ImageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }

if (-not $env:ACCOUNT_ID) {
    $env:ACCOUNT_ID = aws sts get-caller-identity --query Account --output text
}

$AccountId = $env:ACCOUNT_ID
$Registry = "$AccountId.dkr.ecr.$AwsRegion.amazonaws.com"
$IngestionRepo = "$Registry/$ProjectName/ingestion-service"
$RetrievalRepo = "$Registry/$ProjectName/retrieval-service"

Write-Host "==> Logging in to ECR ($AwsRegion)"
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $Registry

Write-Host "==> Building ingestion-service"
docker build -f ingestion-service/Dockerfile -t "${IngestionRepo}:${ImageTag}" .

Write-Host "==> Building retrieval-service"
docker build -f retrieval-service/Dockerfile -t "${RetrievalRepo}:${ImageTag}" .

Write-Host "==> Pushing images"
docker push "${IngestionRepo}:${ImageTag}"
docker push "${RetrievalRepo}:${ImageTag}"

Write-Host ""
Write-Host "Pushed:"
Write-Host "  ${IngestionRepo}:${ImageTag}"
Write-Host "  ${RetrievalRepo}:${ImageTag}"
