terraform {
  source = "${path_relative_from_include()}/../__modules__//vpc"
}

locals {
  global_vars      = read_terragrunt_config(find_in_parent_folders("global.hcl"))
  environment_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))
  region_vars      = read_terragrunt_config(find_in_parent_folders("region.hcl"))

  product_name = local.global_vars.locals.product_name
  environment  = local.environment_vars.locals.environment
  aws_region   = local.region_vars.locals.aws_region
}

inputs = {
  name               = "${local.product_name}-${local.environment}"
  azs                = ["${local.aws_region}a", "${local.aws_region}b"]
  enable_nat_gateway = true
  single_nat_gateway = true
}
