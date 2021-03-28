# Create ALB and related resources (requires VPC)

resource "aws_security_group" "alb_any" {
  name = "test-mangum-alb-allow-all"
  description = "Allow all traffic to mangum alb"

  vpc_id = aws_vpc.mangum.id

  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "mangum" {
  name="test-mangum"
  internal = false
  load_balancer_type = "application"

  subnets = [
    aws_subnet.test_c.id,
    aws_subnet.test_d.id
  ]

  security_groups = [aws_security_group.alb_any.id]

  depends_on = [aws_internet_gateway.mangum] # gee dangit terraform
}

resource "aws_lb_target_group" "mangum_lambda" {
  name = "test-lambda"
  target_type = "lambda"
}

resource "aws_lb_listener" "mangum" {
  load_balancer_arn = aws_lb.mangum.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"

    fixed_response {
      content_type = "text/plain"
      message_body = "Unable to route request"
      status_code  = "404"
    }
  }
}

resource "aws_lambda_permission" "from_alb" {
  statement_id  = "AllowExecutionFromlb"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mangum.arn
  principal     = "elasticloadbalancing.amazonaws.com"
  source_arn    = aws_lb_target_group.mangum_lambda.arn
}

resource "aws_lb_target_group_attachment" "test" {
  target_group_arn = aws_lb_target_group.mangum_lambda.arn
  target_id        = aws_lambda_function.mangum.arn
  depends_on       = [aws_lambda_permission.from_alb]
}

resource "aws_lb_listener_rule" "mangum_primary" {
  listener_arn = aws_lb_listener.mangum.arn
  priority = 100

  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.mangum_lambda.arn
  }

  condition {
    path_pattern {
      values = ["/mangum/*"]
    }
  }
}
