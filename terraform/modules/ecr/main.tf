###############################################
# 1) APP image के लिये ECR repo
###############################################
resource "aws_ecr_repository" "app_repo" {
  name                 = var.repo_name          # ex: app-repo
  image_tag_mutability = "MUTABLE"

  tags = {
    Environment = var.environment
  }
}

###############################################
# 2) SageMaker model image के लिये ECR repo
#    (स्किप करना हो तो  module में  create_model_repo = false  पास कर दें)
###############################################
resource "aws_ecr_repository" "model_repo" {
  count                = var.create_model_repo ? 1 : 0
  name                 = var.model_repo_name   # ex: sklearn-inference
  image_tag_mutability = "IMMUTABLE"           # मॉडल इमेज ज़्यादातर एक-ही tag रहती है

  tags = {
    Environment = var.environment
    Purpose     = "sagemaker-model"
  }
}

###############################################
# 3) UNTAGGED cleanup policy — APP repo
###############################################
resource "aws_ecr_lifecycle_policy" "app_clean_old" {
  repository = aws_ecr_repository.app_repo.name

  policy = <<POLICY
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Expire untagged images older than 7 days",
      "selection": {
        "tagStatus": "untagged",
        "countType": "sinceImagePushed",
        "countUnit": "days",
        "countNumber": 7
      },
      "action": { "type": "expire" }
    }
  ]
}
POLICY
}

###############################################
# 4) SageMaker-pull policy  (ONLY model_repo)
###############################################
resource "aws_ecr_repository_policy" "allow_sagemaker" {
  count      = var.create_model_repo ? 1 : 0
  repository = aws_ecr_repository.model_repo[0].name

  policy = jsonencode({
    Version   = "2008-10-17"
    Statement = [{
      Sid       = "AllowSageMakerService"
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ]
    }]
  })
}
