output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "ecr_repo_url" {
  value = module.ecr.repository_url
}

output "lambda_arn" {
  value = module.lambda.lambda_arn
}

output "sagemaker_endpoint" {
  value = module.sagemaker.endpoint_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}
output "eks_node_group" {
  value = module.eks.node_group_name
}
