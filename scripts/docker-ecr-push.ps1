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
$UploadRepo = "$Registry/$ProjectName/upload-service"
$ProcessingRepo = "$Registry/$ProjectName/data-processing-service"
$RetrievalRepo = "$Registry/$ProjectName/retrieval-service"

Write-Host "==> Logging in to ECR ($AwsRegion)"
aws ecr get-login-password --region $AwsRegion | docker login --username AWS --password-stdin $Registry

Write-Host "==> Building upload-service"
docker build -f upload-service/Dockerfile -t "${UploadRepo}:${ImageTag}" .

Write-Host "==> Building data-processing-service"
docker build -f data-processing-service/Dockerfile -t "${ProcessingRepo}:${ImageTag}" .

Write-Host "==> Building retrieval-service"
docker build -f retrieval-service/Dockerfile -t "${RetrievalRepo}:${ImageTag}" .

Write-Host "==> Pushing images"
docker push "${UploadRepo}:${ImageTag}"
docker push "${ProcessingRepo}:${ImageTag}"
docker push "${RetrievalRepo}:${ImageTag}"

Write-Host ""
Write-Host "Pushed:"
Write-Host "  ${UploadRepo}:${ImageTag}"
Write-Host "  ${ProcessingRepo}:${ImageTag}"
Write-Host "  ${RetrievalRepo}:${ImageTag}"
