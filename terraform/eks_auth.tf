# file: aws_auth.tf   (or whatever your original file was)
resource "kubernetes_config_map" "aws_auth" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }

  data = {
    mapRoles = yamlencode([
      # ---- EKS node role (already there) ----
      {
        rolearn  = module.iam.node_role_arn
        username = "system:node:{{EC2PrivateDNSName}}"
        groups   = ["system:bootstrappers", "system:nodes"]
      },
      # ---- NEW: GitHub Actions role ----
      {
        rolearn  = "arn:aws:iam::311141543250:role/github-actions-role"
        username = "github-actions"
        groups   = ["system:masters"]
      }
    ])

    mapUsers = yamlencode([
      {
        userarn  = "arn:aws:iam::${var.aws_account_id}:user/github-actions-user"
        username = "github-actions-user"
        groups   = ["system:masters"]
      }
    ])
  }

  depends_on = [module.eks]
}
