# ───────── SageMaker model, endpoint-config & endpoint ─────────
resource "aws_cloudformation_stack" "sagemaker" {
  name = "sagemaker-stack-${var.environment}"

  template_body = <<TEMPLATE
AWSTemplateFormatVersion: '2010-09-09'
Resources:

  FailurePredictorModel:
    Type: AWS::SageMaker::Model
    Properties:
      ModelName: !Sub failure-predictor-${var.environment}
      ExecutionRoleArn: ${var.sagemaker_exec_role_arn}

      PrimaryContainer:
        # 🟢 public DLC image (same region, no mirror needed)
        Image: ${var.model_image}                
        ModelDataUrl: ${var.model_data_s3_path}
    
      # VPC config agar aapko endpoint ko private subnet me rakhna hai
      VpcConfig:
        Subnets: ${jsonencode(var.vpc_subnet_ids)}
        SecurityGroupIds: ${jsonencode(var.vpc_sg_ids)}

  EndpointConfig:
    Type: AWS::SageMaker::EndpointConfig
    DependsOn: FailurePredictorModel
    Properties:
      EndpointConfigName: !Sub endpoint-config-${var.environment}
      ProductionVariants:
        - VariantName: AllTraffic
          ModelName: !Sub failure-predictor-${var.environment}
          InitialInstanceCount: ${var.endpoint_instance_count}
          InstanceType: "${var.endpoint_instance_type}"

  FailureEndpoint:
    Type: AWS::SageMaker::Endpoint
    DependsOn: EndpointConfig
    Properties:
      EndpointName: !Sub failure-endpoint-${var.environment}
      EndpointConfigName: !Sub endpoint-config-${var.environment}
TEMPLATE

  capabilities       = ["CAPABILITY_IAM"]
  timeout_in_minutes = 60
}
