resource "aws_s3_object" "folder_structure" {
  for_each = local.s3_prefixes

  bucket  = aws_s3_bucket.documents.id
  key     = each.value
  content = ""
}

locals {
  s3_prefixes = {
    upload     = "upload/"
    processing = "processing/"
    processed  = "processed/"
    failed     = "failed/"
    archived   = "archived/"
  }
}

resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-${var.environment}-documents"

  tags = {
    Name = "${var.project_name}-documents"
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket = aws_s3_bucket.documents.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
