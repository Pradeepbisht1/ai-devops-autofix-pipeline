variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "ap-southeast-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "public_subnets" {
  description = "CIDRs for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  description = "CIDRs for private subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "image_tag" {
  description = "Tag for Docker image"
  type        = string
  default     = "latest"
}

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL"
  type        = string
}

variable "model_data_s3_path" {
  description = "S3 path to model.tar.gz"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID"
  type        = string
}

# Added ECR repository name for Docker image URI construction
variable "ecr_repo" {
  description = "ECR repository name (e.g. app-repo)"
  type        = string
}

# IAM Role ARN that SageMaker uses to execute the model
variable "sagemaker_exec_role_arn" {
  description = "IAM role ARN for SageMaker execution"
  type        = string
}

# Number of instances for the SageMaker endpoint
variable "endpoint_instance_count" {
  description = "Number of instances for the SageMaker endpoint"
  type        = number
  default     = 1
}

# EC2 instance type for the SageMaker endpoint
variable "endpoint_instance_type" {
  description = "EC2 instance type for the SageMaker endpoint"
  type        = string
  default     = "ml.m4.xlarge"
}

variable "model_image" {
  description = "ECR URI of the SageMaker inference container"
  type        = string
}


variable "model_repo_name" {
  description = "ECR repo name for the SageMaker model image"
  type        = string
  default     = "sklearn-inference"
}

variable "create_model_repo" {
  description = "Set false if you already created/push-policy manually"
  type        = bool
  default     = true
}
