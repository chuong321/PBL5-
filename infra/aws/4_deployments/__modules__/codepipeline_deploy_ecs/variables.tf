variable "name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "artifact_buckets" {
  type = map(object({
    bucket_arn     = string
    bucket_id      = string
    encryption_key = optional(string)
  }))
  default = {}
}

variable "artifact_encryption_key" {
  type    = string
  default = null
}

variable "codestar_connection_arn" {
  type = string
}

variable "github_owner" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "branch" {
  type    = string
  default = "main"
}

variable "build_config" {
  description = "Build & test configuration"
  type = object({
    buildspec = string
    environment_variables = optional(list(object({
      name  = string
      value = string
    })), [])
  })
}
