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

