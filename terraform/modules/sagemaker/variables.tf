variable "vpc_subnet_ids" {
  type        = list(string)
  description = "List of private subnet IDs for SageMaker endpoint VPC configuration"
}

variable "vpc_sg_ids" {
  type        = list(string)
  description = "List of security group IDs for SageMaker endpoint VPC configuration"
}

variable "environment" {
  description = "Deployment environment (e.g. prod, dev)"
  type        = string
}

variable "sagemaker_exec_role_arn" {
  description = "IAM role ARN that SageMaker uses to execute the model"
  type        = string
}

variable "model_image" {
  description = "ECR image URI for the SageMaker model container"
  type        = string
}

variable "model_data_s3_path" {
  description = "S3 path to model artifact (model.tar.gz)"
  type        = string
}

variable "endpoint_instance_count" {
  description = "Number of instances for the SageMaker endpoint"
  type        = number
  default     = 1
}

variable "endpoint_instance_type" {
  description = "EC2 instance type for the SageMaker endpoint"
  type        = string
  default     = "ml.m4.xlarge"
}
