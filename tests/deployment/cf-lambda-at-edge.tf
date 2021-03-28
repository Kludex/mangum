resource "aws_cloudfront_distribution" "main_cdn" {
  # Ordered like the AWS Console (Edit distribution)
  price_class = "PriceClass_100"

  aliases = [
  ]

  # SSL Cert
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  http_version = "http2"

  comment = "Mangum Testing"

  is_ipv6_enabled = true

  enabled = true

  origin {
    origin_id   = "mangum-testing"
    domain_name = "www.example.com"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = [
        "TLSv1",
        "TLSv1.1",
        "TLSv1.2",
      ]
    }
    custom_header {
      name  = "x-debug-origin-header"
      value = "true"
    }
  }

  default_cache_behavior {
    # Ordered like the AWS Console
    target_origin_id = "mangum-testing"

    viewer_protocol_policy = "allow-all"

    allowed_methods = [
      "HEAD",
      "DELETE",
      "POST",
      "GET",
      "OPTIONS",
      "PUT",
      "PATCH",
    ]

    cached_methods = [
      "HEAD",
      "GET",
    ]

    forwarded_values {
      headers = ["*"]

      cookies {
        forward = "none"
      }

      query_string = true
    }

    min_ttl     = 0
    max_ttl     = 3600
    default_ttl = 60

    smooth_streaming = false
    trusted_signers  = []
    compress         = true

    lambda_function_association {
      event_type   = "origin-request"
      lambda_arn   = aws_lambda_function.mangum.qualified_arn

      include_body = true
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  custom_error_response {
    error_code            = 400
    error_caching_min_ttl = 60
  }

  custom_error_response {
    error_code            = 403
    error_caching_min_ttl = 900
  }

  custom_error_response {
    error_code            = 404
    error_caching_min_ttl = 900
  }

  custom_error_response {
    error_code            = 500
    error_caching_min_ttl = 30
  }

  custom_error_response {
    error_code            = 502
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 504
    error_caching_min_ttl = 60
  }

  count = local.enable_lambda_at_edge ? 1 : 0
}
