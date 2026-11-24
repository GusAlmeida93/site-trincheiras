# Two functions from one image. "web" serves the site behind CloudFront.
# "ops" is the same app with POST /internal/ops mounted and no URL at all: it
# is reachable only through `aws lambda invoke`, which is how migrations and
# the content seed reach a database that has no public address.

resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the ten most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}

# Resolving the tag to a digest makes a re-pushed tag deploy too.
data "aws_ecr_image" "app" {
  repository_name = aws_ecr_repository.app.name
  image_tag       = var.image_tag
}

resource "random_password" "admin_token" {
  length  = 48
  special = false
}

# Keys the digests of teacher session and invite tokens. Both functions need
# the same value: "ops" issues invite links and "web" checks them. Replacing
# it (terraform apply -replace=random_password.session_secret) signs every
# teacher out and voids outstanding invite links.
resource "random_password" "session_secret" {
  length  = 64
  special = false
}

locals {
  functions = {
    web = {
      timeout = 60
      memory  = 1024
      environment = {
        # One attempt may take 10 s; keep trying for 45 s, inside the 60 s that
        # both this function and CloudFront allow a request.
        DB_CONNECT_RETRY_SECONDS = "45"
      }
    }
    ops = {
      timeout = 300
      memory  = 1024
      environment = {
        OPS_MODE                  = "true"
        AWS_LWA_PASS_THROUGH_PATH = "/internal/ops"
        DB_CONNECT_RETRY_SECONDS  = "120"
      }
    }
  }

  shared_environment = {
    APP_ENV      = "prod"
    PORT         = "8080"
    DATABASE_URL = local.database_url
    ADMIN_TOKEN  = random_password.admin_token.result
    # Enables teacher sign-in at /admin; without it the app keeps it off.
    SESSION_SECRET = random_password.session_secret.result
    # A frozen sandbox must not keep a connection open: Aurora pauses only
    # when none is left.
    DB_POOL            = "false"
    DB_CONNECT_TIMEOUT = "10"
    # "/" renders from the database; /healthz does not, so a sleeping
    # database never delays a cold start.
    AWS_LWA_READINESS_CHECK_PATH = "/healthz"
    # CloudFront does not compress responses it does not cache.
    AWS_LWA_ENABLE_COMPRESSION = "true"
  }
}

data "aws_iam_policy_document" "assume_lambda" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.assume_lambda.json
}

# Logs plus the network interfaces a function inside a VPC needs.
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.functions

  name              = "/aws/lambda/${local.name}-${each.key}"
  retention_in_days = 30
}

resource "aws_lambda_function" "this" {
  for_each = local.functions

  function_name = "${local.name}-${each.key}"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = data.aws_ecr_image.app.image_uri
  architectures = ["arm64"]
  memory_size   = each.value.memory
  timeout       = each.value.timeout

  environment {
    variables = merge(local.shared_environment, each.value.environment)
  }

  vpc_config {
    subnet_ids         = aws_subnet.private[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.lambda[each.key].name
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_vpc]
}

# Only CloudFront may call the URL: it signs each request (SigV4) and Lambda
# checks the signature against the two permissions below.
resource "aws_lambda_function_url" "web" {
  function_name      = aws_lambda_function.this["web"].function_name
  authorization_type = "AWS_IAM"
  invoke_mode        = "BUFFERED"
}

resource "aws_lambda_permission" "cloudfront_url" {
  statement_id           = "cloudfront-invoke-function-url"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.this["web"].function_name
  principal              = "cloudfront.amazonaws.com"
  source_arn             = aws_cloudfront_distribution.this.arn
  function_url_auth_type = "AWS_IAM"
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id             = "cloudfront-invoke-function"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.this["web"].function_name
  principal                = "cloudfront.amazonaws.com"
  source_arn               = aws_cloudfront_distribution.this.arn
  invoked_via_function_url = true
}
