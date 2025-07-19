variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "cluster_role_arn" {
  description = "IAM role ARN for EKS cluster"
  type        = string
}

variable "node_role_arn" {
  description = "IAM role ARN for worker nodes"
  type        = string
}

variable "public_subnets" {
  description = "IDs of public subnets"
  type        = list(string)
}

variable "private_subnets" {
  description = "IDs of private subnets"
  type        = list(string)
}

variable "node_desired_count" {
  description = "Desired number of nodes"
  type        = number
  default     = 2
}

variable "node_max_count" {
  description = "Maximum number of nodes"
  type        = number
  default     = 3
}

variable "node_min_count" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "instance_types" {
  description = "Instance types for the node group"
  type        = list(string)
  default     = ["t3.medium"]
}