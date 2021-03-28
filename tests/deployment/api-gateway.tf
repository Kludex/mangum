resource "aws_api_gateway_rest_api" "mangum" {
  name = "test-mangum"
  body = templatefile("${path.module}/api-gateway.oas30.json", {
    lambda_arn = aws_lambda_function.mangum.arn
  })
}

resource "aws_api_gateway_deployment" "test_deploy" {
  rest_api_id = aws_api_gateway_rest_api.mangum.id

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.mangum.body))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "test_stage" {
  deployment_id = aws_api_gateway_deployment.test_deploy.id
  rest_api_id = aws_api_gateway_rest_api.mangum.id
  stage_name = "test-stage"
  description = "Testing stage"

  variables = {
    testMangumStageVar = "TestTestTest"
  }
}

resource "aws_lambda_permission" "from_api_gateway" {
  statement_id = "AllowExecutionFromApiGateway"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.mangum.arn
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.mangum.execution_arn}/*/*/*"
}
