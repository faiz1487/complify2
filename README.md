AWS Document Microservices

FastAPI upload, data processing, and retrieval services on AWS ECS Fargate, with RDS PostgreSQL, ElastiCache Redis, S3, and SQS.

Images are built with Docker on your machine (or CI) and pushed to ECR — CodeBuild is not used.

Architecture


User → ALB (public)

         ├── Upload Service :4000        POST /api/upload

         └── Retrieval Service :4002     GET /api/search/{filename}

                    │

                    ▼

              S3 upload/

                    │

                    ▼ (S3 event + direct SQS publish)

              SQS Processing Queue

                    │

                    ▼

         Data Processing Service :4003  (private, no ALB)

                    │

         S3 processed/ + PostgreSQL + Redis

                    │

                    ▼

         Retrieval Service → User Response


ECS services

| Service | Port | ALB | Role |

|---------|------|-----|------|

| Upload | 4000 | Yes | Store raw files in S3, persist metadata, queue processing |

| Data Processing | 4003 | No | Consume SQS, chunk, embed, write processed output |

| Retrieval | 4002 | Yes | Search and return document metadata |

S3 prefixes





upload/ — incoming files



processing/ — files being processed



processed/ — processed JSON artifacts



failed/ — failed processing artifacts



archived/ — reserved for lifecycle archival

Data stores





PostgreSQL: users, documents, chunks, chat history



Redis: query cache, sessions, rate limiting, processing scratch state



SQS: event-driven processing pipeline (with DLQ)

Prerequisites





Docker Desktop (running)



AWS CLI configured (aws configure)



Terraform >= 1.5

Runtime (RDS, Redis, S3, ECS, SQS) runs only on AWS. You use Docker only to build and push images to ECR.

Quick deploy

1. Configure Terraform


cd infrastructure/terraform

cp terraform.tfvars.example terraform.tfvars

# Edit db_password in terraform.tfvars


2. One-command deploy (Linux / macOS / Git Bash)


chmod +x scripts/aws-deploy.sh scripts/docker-ecr-push.sh

./scripts/aws-deploy.sh


Windows (PowerShell)


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


Test the API


ALB=$(terraform -chdir=infrastructure/terraform output -raw api_base_url)



curl -s "$ALB/"

curl -s "$ALB/health/upload"



curl -X POST "$ALB/api/upload" -F "file=@./README.md"

curl -s "$ALB/api/search/README.md"

curl -s "$ALB/api/documents/1"


| Wrong | Correct |

|-------|---------|

| GET /api/upload | POST /api/upload with -F "file=@..." |

| /api/search | /api/search/filename.pdf |

| /health/ingestion | /health/upload or /health/retrieval |

Upload returns 202 Accepted with status: pending. Poll search until status: processed.

Redeploy after code changes


./scripts/docker-ecr-push.sh    # or docker-ecr-push.ps1

./scripts/deploy-ecs.sh


Environment on ECS

Set by Terraform on Fargate tasks: DB_*, REDIS_*, S3_BUCKET, S3_PREFIX_*, SQS_QUEUE_URL, AWS_REGION.  

DB_PASSWORD comes from Secrets Manager. S3 and SQS use the ECS task IAM role.

Optional: set openai_api_key in terraform.tfvars for OpenAI embeddings; otherwise hash-based embeddings are used.

Project layout


├── upload-service/              Port 4000, POST /api/upload

├── data-processing-service/     Port 4003, SQS consumer

├── retrieval-service/           Port 4002, GET /api/search

├── shared/                      Common DB, Redis, S3, SQS code

├── infrastructure/terraform/    VPC, RDS, Redis, S3, SQS, ECS, ALB, autoscaling

├── scripts/

│   ├── docker-ecr-push.sh

│   ├── docker-ecr-push.ps1

│   ├── aws-deploy.sh

│   └── deploy-ecs.sh

└── README.md


Destroy stack


cd infrastructure/terraform

terraform destroy


ECS Service Configuration

Terraform in infrastructure/terraform/ is the source of truth. This document describes the deployed topology.

Services

| ECS Service | Container | Port | ALB | Subnets |

|-------------|-----------|------|-----|---------|

| upload-service | upload-service | 4000 | Yes | Private |

| data-processing-service | data-processing-service | 4003 | No | Private |

| retrieval-service | retrieval-service | 4002 | Yes | Private |

ALB routing

| Path | Target |

|------|--------|

| POST /api/upload | upload-service :4000 |

| /api/upload/* | upload-service :4000 |

| GET /api/search/* | retrieval-service :4002 |

| GET /api/documents/* | retrieval-service :4002 |

| /docs* | upload-service :4000 (Swagger UI) |

| /openapi.json | upload-service :4000 |

| GET /health/upload | upload-service :4000 |

| GET /health/retrieval | retrieval-service :4002 |

Event flow





Upload service writes to s3://{bucket}/upload/



S3 event notification and direct SQS publish enqueue processing jobs



Data processing service consumes SQS, moves objects through prefixes, writes chunks to PostgreSQL



Retrieval service reads metadata from PostgreSQL/Redis

Auto scaling

CPU target tracking (default 70%) on all three ECS services. Min 1, max 6 tasks per service (configurable in variables.tf).

Security groups





ALB: ingress 80 from internet



ECS (upload/retrieval): ingress 4000/4002 from ALB



ECS (processing): egress only (internal worker)



RDS: 5432 from ECS task SGs



Redis: 6379 from ECS task SGs

