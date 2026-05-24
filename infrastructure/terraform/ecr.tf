resource "aws_ecr_repository" "ingestion" {
  name                 = "${var.project_name}/ingestion-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "retrieval" {
  name                 = "${var.project_name}/retrieval-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = false

  image_scanning_configuration {
    scan_on_push = true
  }
}
