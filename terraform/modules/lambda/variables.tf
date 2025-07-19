variable "environment" {
  description = "Deployment environment (e.g. dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role that Lambda will assume"
  type        = string
}

variable "package_zip_path" {
  description = "Path to the Lambda deployment ZIP file"
  type        = string
}

variable "handler" {
  description = "Lambda function handler (module.function)"
  type        = string
  default     = "smart_auto_heal.handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.10"
}

variable "memory_size" {
  description = "Amount of memory (MB) allocated to the Lambda function"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Timeout (seconds) for the Lambda function"
  type        = number
  default     = 30
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL for notifications"
  type        = string
}

variable "lambda_subnet_ids" {
  description = "List of subnet IDs (in VPC) for Lambda to run in"
  type        = list(string)
  default     = []
}

variable "lambda_security_group_ids" {
  description = "List of security group IDs for Lambda to use"
  type        = list(string)
  default     = []
}

variable "lambda_log_retention_days" {
  description = "Number of days to retain Lambda CloudWatch logs"
  type        = number
  default     = 14
}
