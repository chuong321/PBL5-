variable "tags" {
  type    = map(string)
  default = {}
}

variable "name" {
  type = string
}

variable "cluster_arn" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "vpc_id" {
  type = string
}

variable "alb_security_group_id" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "container_name" {
  type    = string
  default = "app"
}

variable "container_image" {
  description = "Full image URI including tag, e.g. 123456.dkr.ecr.ap-southeast-1.amazonaws.com/trash-classification:latest"
  type        = string
}

variable "container_port" {
  type    = number
  default = 8000
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "environment_variables" {
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}
