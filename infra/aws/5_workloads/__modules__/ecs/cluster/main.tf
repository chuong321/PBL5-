#==============================================================================
# ECS Cluster
#==============================================================================

resource "aws_ecs_cluster" "this" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = var.containerInsights
  }

  tags = merge(
    { Name = var.cluster_name },
    var.tags,
  )
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

#==============================================================================
# CloudWatch Log Group
#==============================================================================

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/ecs/${var.cluster_name}"
  retention_in_days = var.cloudwatch_log_group_retention_in_days

  tags = merge(
    { Name = "/aws/ecs/${var.cluster_name}" },
    var.tags,
  )
}

#==============================================================================
# Application Load Balancer
#==============================================================================

resource "aws_security_group" "alb" {
  name        = "${var.cluster_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.private_subnets_cidr_blocks
  }

  tags = merge(
    { Name = "${var.cluster_name}-alb-sg" },
    var.tags,
  )
}

resource "aws_lb" "this" {
  name               = "${var.cluster_name}-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnets

  tags = merge(
    { Name = "${var.cluster_name}-alb" },
    var.tags,
  )
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "forward"
    target_group_arn = aws_lb_target_group.default.arn
  }
}

resource "aws_lb_target_group" "default" {
  name        = "${var.cluster_name}-default-tg"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/api/health"
    protocol            = "HTTP"
    port                = "8000"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }

  tags = var.tags
}
