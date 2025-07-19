// modules/iam/outputs.tf

output "node_role_arn" {
  description = "ARN for the EKS worker node IAM role"
  value       = aws_iam_role.eks_node_role.arn
}

output "cluster_role_arn" {
  description = "ARN for the EKS control plane IAM role"
  value       = aws_iam_role.eks_cluster_role.arn
}

output "lambda_exec_role_arn" {
  description = "ARN for the Lambda execution IAM role"
  value       = aws_iam_role.lambda_exec.arn
}

output "sagemaker_exec_role_arn" {
  description = "ARN for the SageMaker execution IAM role"
  value       = aws_iam_role.sagemaker_exec.arn
}
output "github_actions_access_key_id" {
  value     = aws_iam_access_key.github_actions_key.id
  sensitive = true
}

output "github_actions_secret_access_key" {
  value     = aws_iam_access_key.github_actions_key.secret
  sensitive = true
}

output "github_actions_user_arn" {
  value = aws_iam_user.github_actions_user.arn
}

