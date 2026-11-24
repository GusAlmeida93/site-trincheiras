# A private network with no way in or out: no internet gateway, no NAT.
# Lambda reaches Aurora inside it and nothing else needs to. That also keeps
# it free, since NAT gateways and VPC endpoints are what cost money here.

locals {
  name = "trincheiras"
  azs  = slice(data.aws_availability_zones.available.names, 0, 2)
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = local.name }
}

resource "aws_subnet" "private" {
  count = length(local.azs)

  vpc_id            = aws_vpc.this.id
  availability_zone = local.azs[count.index]
  cidr_block        = cidrsubnet(aws_vpc.this.cidr_block, 8, count.index)

  tags = { Name = "${local.name}-private-${local.azs[count.index]}" }
}

resource "aws_security_group" "lambda" {
  name        = "${local.name}-lambda"
  description = "The web and ops functions"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${local.name}-lambda" }
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "The Aurora cluster"
  vpc_id      = aws_vpc.this.id

  tags = { Name = "${local.name}-db" }
}

resource "aws_vpc_security_group_egress_rule" "lambda_to_db" {
  security_group_id            = aws_security_group.lambda.id
  description                  = "PostgreSQL to the cluster"
  referenced_security_group_id = aws_security_group.db.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_ingress_rule" "db_from_lambda" {
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL from the functions"
  referenced_security_group_id = aws_security_group.lambda.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}
