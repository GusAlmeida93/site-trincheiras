terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.66"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  # Created once by hand, see infra/README.md.
  backend "s3" {
    bucket       = "trincheiras-terraform-state-249744179072"
    key          = "site/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}

# One region for everything: CloudFront only accepts certificates from
# us-east-1, and CloudFront's edge in Brazil keeps the static assets close to
# the classroom.
provider "aws" {
  region              = "us-east-1"
  allowed_account_ids = ["249744179072"]

  default_tags {
    tags = {
      Project   = "site-trincheiras"
      ManagedBy = "terraform"
    }
  }
}
