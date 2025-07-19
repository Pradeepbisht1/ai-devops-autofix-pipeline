
output "model_name" {
  description = "Name of the SageMaker model"
  value       = "failure-predictor-${var.environment}"
}

output "endpoint_configuration_name" {
  description = "Name of the SageMaker endpoint configuration"
  value       = "endpoint-config-${var.environment}"
}

output "endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = "failure-endpoint-${var.environment}"
}
