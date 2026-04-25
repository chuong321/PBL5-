variable "name" {
  description = "Name of the CodeBuild project"
  type        = string
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "buildspec" {
  description = "Buildspec content"
  type        = string
  default     = ""
}

variable "build_timeout" {
  description = "Build timeout in minutes"
  type        = number
  default     = 15
}

variable "build_image" {
  description = "Docker image for build environment"
  type        = string
  default     = "aws/codebuild/standard:7.0"
}

variable "build_compute_type" {
  description = "Instance type of the build instance"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "source_type" {
  description = "Source type: CODEPIPELINE, GITHUB, etc."
  type        = string
  default     = "CODEPIPELINE"
}

variable "artifact_type" {
  description = "Artifact type: CODEPIPELINE, NO_ARTIFACTS, S3"
  type        = string
  default     = "CODEPIPELINE"
}

variable "cache_type" {
  description = "Cache type: NO_CACHE, LOCAL, S3"
  type        = string
  default     = "NO_CACHE"
}

variable "local_cache_modes" {
  description = "Local cache modes"
  type        = list(string)
  default     = []
}

variable "encryption_key" {
  description = "KMS key ARN for encrypting build artifacts"
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "Environment variables for the build"
  type = list(object({
    name  = string
    value = string
    type  = optional(string)
  }))
  default = []
}

variable "codebuild_iam_role_statements" {
  description = "Additional IAM policy statements"
  type        = any
  default     = []
}
