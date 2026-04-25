variable "tags" {
  type    = map(string)
  default = {}
}

variable "cluster_name" {
  type = string
}

variable "containerInsights" {
  type    = string
  default = "enabled"
}

variable "cloudwatch_log_group_retention_in_days" {
  type    = number
  default = 14
}

variable "vpc_id" {
  type = string
}

variable "public_subnets" {
  type    = list(string)
  default = []
}

variable "private_subnets_cidr_blocks" {
  type    = list(string)
  default = []
}
