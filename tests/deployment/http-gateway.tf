resource "aws_apigatewayv2_api" "mangum_http" {
  name = "test-mangum-http"
  protocol_type = "HTTP"
  body = templatefile("${path.module}/http-gateway.oas30.json", {
    lambda_arn = aws_lambda_function.mangum.arn
  })
}

resource "aws_apigatewayv2_route" "mangum_http" {
  api_id    = aws_apigatewayv2_api.mangum_http.id
  route_key = "$default"
}

resource "aws_apigatewayv2_deployment" "mangum_http" {
  api_id      = aws_apigatewayv2_route.mangum_http.api_id
  description = "Example deployment"

  triggers = {
    redeployment = sha1(jsonencode(aws_apigatewayv2_api.mangum_http.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_apigatewayv2_stage" "mangum_http" {
  api_id = aws_apigatewayv2_api.mangum_http.id
  name   = "test-stage"
}

resource "aws_lambda_permission" "from_http_gateway" {
  statement_id = "AllowExecutionFromHttpGateway"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mangum.arn
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.mangum_http.execution_arn}/*/*/"
}
