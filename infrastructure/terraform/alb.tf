resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_target_group" "ingestion" {
  name        = "${var.project_name}-ingestion-tg"
  port        = 4001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
}

resource "aws_lb_target_group" "retrieval" {
  name        = "${var.project_name}-retrieval-tg"
  port        = 4002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "application/json"
      message_body = "{\"message\":\"Document API\",\"upload\":\"POST /api/upload\",\"search\":\"GET /api/search/{filename}\",\"health_ingestion\":\"GET /health/ingestion\",\"health_retrieval\":\"GET /health/retrieval\"}"
      status_code  = "200"
    }
  }
}

resource "aws_lb_listener_rule" "health_ingestion" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 50

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ingestion.arn
  }

  condition {
    path_pattern {
      values = ["/health/ingestion", "/health/ingestion/*"]
    }
  }
}

resource "aws_lb_listener_rule" "health_retrieval" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 60

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.retrieval.arn
  }

  condition {
    path_pattern {
      values = ["/health/retrieval", "/health/retrieval/*"]
    }
  }
}

resource "aws_lb_listener_rule" "upload" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ingestion.arn
  }

  condition {
    path_pattern {
      values = ["/api/upload", "/api/upload/*", "/api/upload/"]
    }
  }
}

resource "aws_lb_listener_rule" "search" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.retrieval.arn
  }

  condition {
    path_pattern {
      values = ["/api/search/*"]
    }
  }
}
