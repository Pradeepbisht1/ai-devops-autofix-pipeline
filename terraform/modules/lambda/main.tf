resource "aws_lambda_function" "auto_heal" {
  function_name     = "auto-heal-${var.environment}"
  role              = var.lambda_role_arn
  handler           = "smart_auto_heal.handler"
  runtime           = "python3.10"
  filename          = var.package_zip_path
  source_code_hash  = filebase64sha256(var.package_zip_path)
  publish           = true                  # ensure a new version is created

  # PERFORMANCE & RELIABILITY
  memory_size       = var.memory_size
  timeout           = var.timeout

  # ENVIRONMENT
  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  # X-RAY TRACING
  tracing_config {
    mode = "Active"
  }

  # VPC (if you need access to private subnets/services)
  vpc_config {
    subnet_ids         = var.lambda_subnet_ids       # list(string)
    security_group_ids = var.lambda_security_group_ids
  }

  tags = {
    Environment = var.environment
    Module      = "auto_heal_lambda"
    Terraform   = "true"
  }
}

# CloudWatch Log Group with retention
data "aws_cloudwatch_log_group" "auto_heal" {
  name = "/aws/lambda/auto-heal-prod"
}

