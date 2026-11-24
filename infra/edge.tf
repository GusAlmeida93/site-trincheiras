# CloudFront in front of the web function: TLS, the custom domain, and an
# edge cache for /static/* so images and bundles never wake Lambda twice.

locals {
  site_hosts = [var.domain_name, "www.${var.domain_name}"]

  # AWS-managed policies, by their fixed ids.
  managed_policy = {
    caching_disabled       = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    caching_optimized      = "658327ea-f89d-4fab-a63d-7e88639e58f6"
    all_viewer_except_host = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
    security_headers       = "67f7725c-6f97-4210-82d7-5512b31e9d03"
  }
}

resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "${local.name}-lambda"
  description                       = "Signs every request to the web function URL"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "redirect_www" {
  name    = "${local.name}-redirect-www"
  runtime = "cloudfront-js-2.0"
  comment = "Sends www.${var.domain_name} to ${var.domain_name}"
  publish = true
  code    = templatefile("${path.module}/edge/redirect-www.js", { apex = var.domain_name })
}

resource "aws_cloudfront_distribution" "this" {
  comment         = "site-trincheiras"
  enabled         = true
  is_ipv6_enabled = true
  http_version    = "http2and3"
  # The cheaper classes leave out South America, where the students are.
  price_class = "PriceClass_All"
  aliases     = var.domain_delegated ? local.site_hosts : []

  origin {
    origin_id                = "web"
    domain_name              = trimsuffix(trimprefix(aws_lambda_function_url.web.function_url, "https://"), "/")
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda.id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
      # Room for Aurora to wake up on the first request after a pause.
      origin_read_timeout = 60
    }
  }

  default_cache_behavior {
    target_origin_id           = "web"
    allowed_methods            = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods             = ["GET", "HEAD"]
    viewer_protocol_policy     = "redirect-to-https"
    cache_policy_id            = local.managed_policy.caching_disabled
    origin_request_policy_id   = local.managed_policy.all_viewer_except_host
    response_headers_policy_id = local.managed_policy.security_headers
    compress                   = false

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.redirect_www.arn
    }
  }

  ordered_cache_behavior {
    path_pattern               = "/static/*"
    target_origin_id           = "web"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    viewer_protocol_policy     = "redirect-to-https"
    cache_policy_id            = local.managed_policy.caching_optimized
    response_headers_policy_id = local.managed_policy.security_headers
    compress                   = true
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = !var.domain_delegated
    acm_certificate_arn            = var.domain_delegated ? aws_acm_certificate_validation.site[0].certificate_arn : null
    ssl_support_method             = var.domain_delegated ? "sni-only" : null
    minimum_protocol_version       = var.domain_delegated ? "TLSv1.2_2021" : "TLSv1"
  }
}
