# AWS Document Microservices

FastAPI **ingestion** and **retrieval** services on **AWS ECS Fargate**, with **RDS PostgreSQL**, **ElastiCache Redis**, and **S3**.

**Images are built with Docker** on your machine (or CI) and pushed to **ECR** — CodeBuild is not used.

## Architecture

```
Internet → ALB → ECS Fargate (private)
                    ├── ingestion-service :4001  POST /api/upload
                    └── retrieval-service :4002  GET /api/search/{filename}
                 → RDS | Redis | S3
```

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running)
- [AWS CLI](https://aws.amazon.com/cli/) configured (`aws configure`)
- [Terraform](https://www.terraform.io/downloads) >= 1.5

Runtime (RDS, Redis, S3, ECS) runs **only on AWS**. You use Docker only to **build and push** images to ECR.

## Quick deploy

### 1. Configure Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit db_password in terraform.tfvars
```

### 2. One-command deploy (Linux / macOS / Git Bash)

```bash
chmod +x scripts/aws-deploy.sh scripts/docker-ecr-push.sh
./scripts/aws-deploy.sh
```

### Windows (PowerShell)

```powershell
cd infrastructure\terraform
copy terraform.tfvars.example terraform.tfvars
# Edit db_password

cd ..\..
terraform -chdir=infrastructure/terraform init
terraform -chdir=infrastructure/terraform apply -auto-approve -var="app_ready=false"

$env:AWS_REGION = terraform -chdir=infrastructure/terraform output -raw aws_region
$env:PROJECT_NAME = terraform -chdir=infrastructure/terraform output -raw project_name
.\scripts\docker-ecr-push.ps1

terraform -chdir=infrastructure/terraform apply -auto-approve -var="app_ready=true"
.\scripts\deploy-ecs.sh
```

## Manual steps

### A. Create AWS infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform apply -var="app_ready=false"
```

### B. Build with Docker and push to ECR

**Bash:**

```bash
export AWS_REGION=us-east-1
export PROJECT_NAME=document-services
export IMAGE_TAG=latest
./scripts/docker-ecr-push.sh
```

**PowerShell:**

```powershell
$env:AWS_REGION = "us-east-1"
$env:PROJECT_NAME = "document-services"
$env:IMAGE_TAG = "latest"
.\scripts\docker-ecr-push.ps1
```

**Or manually:**

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker build -f ingestion-service/Dockerfile -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/document-services/ingestion-service:latest .
docker build -f retrieval-service/Dockerfile -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/document-services/retrieval-service:latest .

docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/document-services/ingestion-service:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/document-services/retrieval-service:latest
```

### C. Start ECS services

```bash
terraform apply -var="app_ready=true"
./scripts/deploy-ecs.sh
```

## Test the API

```bash
ALB=$(terraform -chdir=infrastructure/terraform output -raw api_base_url)

curl -s "$ALB/"
curl -s "$ALB/health/ingestion"

curl -X POST "$ALB/api/upload" -F "file=@./README.md"
curl -s "$ALB/api/search/README.md"
```

| Wrong | Correct |
|-------|---------|
| `GET /api/upload` | `POST /api/upload` with `-F "file=@..."` |
| `/api/search` | `/api/search/filename.pdf` |
| `/health` | `/health/ingestion` or `/health/retrieval` |

## Redeploy after code changes

```bash
./scripts/docker-ecr-push.sh    # or docker-ecr-push.ps1
./scripts/deploy-ecs.sh
```

## Environment on ECS

Set by Terraform on Fargate tasks: `DB_*`, `REDIS_*`, `S3_BUCKET`, `AWS_REGION`.  
`DB_PASSWORD` comes from **Secrets Manager**. S3 uses the **ECS task IAM role** (no keys in the container).

## Project layout

```
├── ingestion-service/     Dockerfile, FastAPI app
├── retrieval-service/     Dockerfile, FastAPI app
├── shared/                Common DB, Redis, S3 code
├── infrastructure/terraform/
├── scripts/
│   ├── docker-ecr-push.sh   # Docker build + ECR push
│   ├── docker-ecr-push.ps1
│   ├── aws-deploy.sh        # Full deploy
│   └── deploy-ecs.sh        # ECS rolling restart
└── README.md
```

## Destroy stack

```bash
cd infrastructure/terraform
terraform destroy
```
