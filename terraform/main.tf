#################################################
# 0) Local image URI (if you build/push your own)
#################################################
locals {
  model_image_uri = "${module.ecr.repository_url}:${var.image_tag}"
}

#################################################
# 1) VPC Module
#################################################
module "vpc" {
  source          = "./modules/vpc"
  environment     = var.environment
  public_subnets  = var.public_subnets    # e.g. ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets = var.private_subnets   # e.g. ["10.0.101.0/24", "10.0.102.0/24"]
}

#################################################
# 2) IAM Module
#################################################
module "iam" {
  source      = "./modules/iam"
  environment = var.environment
}

#################################################
# 3) ECR Module
#################################################
module "ecr" {
  source      = "./modules/ecr"
  repo_name   = var.environment == "prod" ? "app-repo" : "app-repo-${var.environment}"
  environment = var.environment

  create_model_repo = false
  model_repo_name   = "sklearn-inference"
}



#################################################
# 4) EKS Module
#################################################
module "eks" {
  source           = "./modules/eks"
  environment      = var.environment
  cluster_role_arn = module.iam.cluster_role_arn
  node_role_arn    = module.iam.node_role_arn
  public_subnets   = module.vpc.public_subnet_ids
  private_subnets  = module.vpc.private_subnet_ids
}

#################################################
# 5) Lambda Module (for auto-heal script)
#################################################
module "lambda" {
  source           = "./modules/lambda"
  lambda_role_arn  = module.iam.lambda_exec_role_arn
  package_zip_path = "../pipeline/scripts/smart_auto_heal.py.zip"
  slack_webhook_url = var.slack_webhook_url
  environment       = var.environment
}

#################################################
# 6) Security Group for SageMaker endpoint
#################################################
resource "aws_security_group" "sg_for_sagemaker" {
  name        = "sagemaker-sg-${var.environment}"
  description = "Allow HTTPS to SageMaker endpoint"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "sagemaker-endpoint-sg"
    Environment = var.environment
  }
}

#################################################
# 7) SageMaker Module
#################################################
module "sagemaker" {
  source                  = "./modules/sagemaker"
  environment             = var.environment
  sagemaker_exec_role_arn = var.sagemaker_exec_role_arn

  model_image             = "311141543250.dkr.ecr.ap-southeast-2.amazonaws.com/sklearn-inference:1.2-1-cpu-py3"

  model_data_s3_path      = var.model_data_s3_path
  endpoint_instance_count = var.endpoint_instance_count
  endpoint_instance_type  = var.endpoint_instance_type

  vpc_subnet_ids = module.vpc.private_subnet_ids
  vpc_sg_ids     = [aws_security_group.sg_for_sagemaker.id]
}
