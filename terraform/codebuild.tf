# 1) IAM Role for CodeBuild
resource "aws_iam_role" "codebuild_role" {
  name               = "codebuild-sklearn-mirror-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "codebuild.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

# 2) IAM Role Policy (ECR + CloudWatch Logs)
resource "aws_iam_role_policy" "codebuild_policy" {
  name   = "codebuild-ecr-logs-access"
  role   = aws_iam_role.codebuild_role.id
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      }
    ]
  })
}

# 3) CodeBuild Project
resource "aws_codebuild_project" "mirror_sklearn" {
  name          = "mirror-sklearn-inference"
  service_role  = aws_iam_role.codebuild_role.arn
  build_timeout = 20

  artifacts { type = "NO_ARTIFACTS" }

  environment {
    compute_type    = "BUILD_GENERAL1_MEDIUM"
    image           = "aws/codebuild/standard:5.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true

    environment_variable {
      name  = "ACCOUNT_ID"
      value = var.aws_account_id
    }
    environment_variable {
      name  = "REGION"
      value = var.aws_region
    }
  }

  source {
    type      = "NO_SOURCE"
    buildspec = <<BUILD_SPEC
version: 0.2

phases:
  pre_build:
    commands:
      - aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin 783357654285.dkr.ecr.$REGION.amazonaws.com
      - aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

  build:
    commands:
      - docker pull 783357654285.dkr.ecr.$REGION.amazonaws.com/sagemaker-scikit-learn:1.2-1
      - docker tag 783357654285.dkr.ecr.$REGION.amazonaws.com/sagemaker-scikit-learn:1.2-1 $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/sklearn-inference:1.2-1
      - docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/sklearn-inference:1.2-1
BUILD_SPEC
  }

  # CloudWatch Logs configuration
  logs_config {
    cloudwatch_logs {
      status      = "ENABLED"
      group_name  = "/aws/codebuild/mirror-sklearn-inference"
      stream_name = "mirror-sklearn-inference"
    }
  }
}
