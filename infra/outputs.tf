output "name_servers" {
  description = "Enter these four at registro.br as the domain's DNS servers."
  value       = aws_route53_zone.site.name_servers
}

output "site_url" {
  description = "Where the site answers right now."
  value       = var.domain_delegated ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "cloudfront_url" {
  description = "The distribution's own address; works with or without the custom domain."
  value       = "https://${aws_cloudfront_distribution.this.domain_name}"
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "ops_function_name" {
  value = aws_lambda_function.this["ops"].function_name
}

output "admin_token" {
  description = "X-Admin-Token for /api/v1/admin and /api/v1/reports. Read it with `terraform output -raw admin_token`."
  value       = random_password.admin_token.result
  sensitive   = true
}
