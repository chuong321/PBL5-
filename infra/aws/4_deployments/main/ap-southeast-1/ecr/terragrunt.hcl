terraform {
  source = "../../../__modules__//ecr"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
}

locals {
  global_vars  = read_terragrunt_config(find_in_parent_folders("global.hcl"))
  product_name = local.global_vars.locals.product_name
}

inputs = {
  name = local.product_name
}
