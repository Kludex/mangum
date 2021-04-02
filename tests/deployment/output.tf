output "alb_url" {
  value = "http://${aws_lb.mangum.dns_name}/mangum/"
}

output "api_gateway_endpoint" {
  value = aws_api_gateway_stage.test_stage.invoke_url
}

output "cf_lambda_at_edge_url" {
  value = local.enable_lambda_at_edge ? "http://${aws_cloudfront_distribution.main_cdn[0].domain_name}" : "[disabled in config.tf]"
}

output "http_gateway_endpoint" {
  # Default route (no trailing slash gives a 500, I have no idea why)
  value = "${aws_apigatewayv2_stage.mangum_http.invoke_url}/"
}
