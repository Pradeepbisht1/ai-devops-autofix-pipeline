provider "aws" {
  region = var.aws_region
}

provider "kubernetes" {
  host                   = data.aws_eks_cluster.this.endpoint
  cluster_ca_certificate = base64decode(
    data.aws_eks_cluster.this.certificate_authority[0].data
  )
  token       = data.aws_eks_cluster_auth.this.token
  config_path = ""  # Disable loading any local kubeconfig
}
