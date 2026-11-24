# The zone exists from the first apply so that its name servers can be given
# to registro.br, which checks that they answer for the domain before it
# accepts them. Everything that depends on the delegation waits for
# domain_delegated.

resource "aws_route53_zone" "site" {
  name    = var.domain_name
  comment = "site-trincheiras"
}

resource "aws_acm_certificate" "site" {
  count = var.domain_delegated ? 1 : 0

  domain_name               = var.domain_name
  subject_alternative_names = ["www.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  for_each = var.domain_delegated ? toset(local.site_hosts) : toset([])

  zone_id         = aws_route53_zone.site.zone_id
  allow_overwrite = true
  ttl             = 300

  name = one([
    for option in aws_acm_certificate.site[0].domain_validation_options :
    option.resource_record_name if option.domain_name == each.key
  ])
  type = one([
    for option in aws_acm_certificate.site[0].domain_validation_options :
    option.resource_record_type if option.domain_name == each.key
  ])
  records = [one([
    for option in aws_acm_certificate.site[0].domain_validation_options :
    option.resource_record_value if option.domain_name == each.key
  ])]
}

resource "aws_acm_certificate_validation" "site" {
  count = var.domain_delegated ? 1 : 0

  certificate_arn         = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]
}

resource "aws_route53_record" "site" {
  for_each = var.domain_delegated ? {
    for pair in setproduct(local.site_hosts, ["A", "AAAA"]) : "${pair[0]}/${pair[1]}" => {
      host = pair[0]
      type = pair[1]
    }
  } : {}

  zone_id = aws_route53_zone.site.zone_id
  name    = each.value.host
  type    = each.value.type

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}
