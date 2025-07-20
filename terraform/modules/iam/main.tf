// ────────────────────────────────────────────────────────────────────────────
// EKS Worker Node Role
resource "aws_iam_role" "eks_node_role" {
  name               = "eks-node-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.eks_node_assume.json
}

data "aws_iam_policy_document" "eks_node_assume" {
  statement {
    actions    = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "eks_worker_attach" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_attach" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ec2_registry_attach" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

// ────────────────────────────────────────────────────────────────────────────
// EKS Cluster Role (Control Plane)
resource "aws_iam_role" "eks_cluster_role" {
  name               = "eks-cluster-role-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.eks_cluster_assume.json
}

data "aws_iam_policy_document" "eks_cluster_assume" {
  statement {
    actions    = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "eks_cluster_attach" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

// ────────────────────────────────────────────────────────────────────────────
// Lambda Execution Role
resource "aws_iam_role" "lambda_exec" {
  name               = "lambda-exec-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions    = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_xray_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

// ────────────────────────────────────────────────────────────────────────────
// SageMaker Execution Role
resource "aws_iam_role" "sagemaker_exec" {
  name               = "sagemaker-exec-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_assume.json
}

data "aws_iam_policy_document" "sagemaker_assume" {
  statement {
    actions    = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_s3_readonly" {
  role       = aws_iam_role.sagemaker_exec.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

// ────────────────────────────────────────────────────────────────────────────
// GitHub Actions IAM User (for GitHub CI/CD)
resource "aws_iam_user" "github_actions_user" {
  name = "github-actions-user"
}

resource "aws_iam_access_key" "github_actions_key" {
  user = aws_iam_user.github_actions_user.name
}

resource "aws_iam_user_policy_attachment" "github_actions_eks_access" {
  user       = aws_iam_user.github_actions_user.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_user_policy_attachment" "github_actions_ecr_access" {
  user       = aws_iam_user.github_actions_user.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

resource "aws_iam_user_policy_attachment" "github_actions_admin" {
  user       = aws_iam_user.github_actions_user.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

// ────────────────────────────────────────────────────────────────────────────
// GitHub Actions S3 Put Policy (model uploads)
resource "aws_iam_policy" "github_actions_s3_put" {
  name        = "github-actions-s3-put"
  description = "Allow GitHub Actions to upload model artifacts to ai-devops-models-prod bucket"
  policy      = jsonencode({
    Version   = "2012-10-17",
    Statement = [
      {
        Sid      = "PutModelArtifacts",
        Effect   = "Allow",
        Action   = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ],
        Resource = "arn:aws:s3:::ai-devops-models-prod/*"
      }
    ]
  })
}

# OIDC‑based GitHub Actions role is created outside this module.
# Import its details and attach the policy.
data "aws_iam_role" "github_actions_role" {
  name = "github-actions-role"  # must match role that GitHub Actions assumes (secrets.AWS_ROLE_ARN)
}

resource "aws_iam_role_policy_attachment" "github_actions_s3_put_attach" {
  role       = data.aws_iam_role.github_actions_role.name
  policy_arn = aws_iam_policy.github_actions_s3_put.arn
}
