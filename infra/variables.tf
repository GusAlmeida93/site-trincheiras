variable "domain_name" {
  description = "Apex domain of the site. www.<domain> redirects to it."
  type        = string
}

variable "domain_delegated" {
  description = <<-EOT
    False until registro.br points the domain at this zone's name servers.
    While false the site answers only on its cloudfront.net address; the
    certificate, the CloudFront aliases and the DNS records are created when
    this turns true (ACM cannot validate a certificate for a domain whose DNS
    it cannot see).
  EOT
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "Tag of the image in ECR to run. deploy.sh passes the git commit."
  type        = string
}

variable "db_max_capacity" {
  description = "Upper bound of the Aurora Serverless v2 cluster, in ACUs. The lower bound is 0 (paused)."
  type        = number
  default     = 2
}

variable "db_seconds_until_auto_pause" {
  description = "Idle seconds before Aurora pauses. 300 is the minimum AWS allows."
  type        = number
  default     = 300
}
