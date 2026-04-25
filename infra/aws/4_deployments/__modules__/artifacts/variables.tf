variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "artifact_encryption_key" {
  description = "KMS key ARN for encrypting the artifact bucket"
  type        = string
  default     = null
}
