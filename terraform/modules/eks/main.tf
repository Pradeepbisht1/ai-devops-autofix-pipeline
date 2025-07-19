resource "aws_eks_cluster" "this" {
  name     = "ai-devops-eks-${var.environment}"
  role_arn = var.cluster_role_arn

  vpc_config {
    subnet_ids = var.private_subnets
  }
}

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "workers-${var.environment}"
  node_role_arn   = var.node_role_arn
  subnet_ids      = var.private_subnets

  scaling_config {
    desired_size = var.node_desired_count
    max_size     = var.node_max_count
    min_size     = var.node_min_count
  }

  instance_types = var.instance_types
}