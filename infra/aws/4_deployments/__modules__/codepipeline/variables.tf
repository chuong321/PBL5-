variable "name" {
  type    = string
  default = ""
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
  type    = string
  default = null
}

variable "codestar_repository_id" {
  type    = string
  default = null
}

variable "stages" {
  type = any
}
