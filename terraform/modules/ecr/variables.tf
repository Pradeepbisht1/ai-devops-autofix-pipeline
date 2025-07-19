variable "repo_name" {
  type = string
}
variable "environment" {
  type    = string
  default = "prod"
}

variable "model_repo_name" {
  description = "ECR repository where the sklearn model image will live (e.g. sklearn-inference)."
  type        = string
  default     = "sklearn-inference"
}

variable "create_model_repo" {
  description = "true ⇒ module repo banayega ; false ⇒ existing repo use karega"
  type        = bool
  default     = false   # ⚠️  change kiya: repo already exists so skip creation
}

