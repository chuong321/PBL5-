terraform {
  source = "${path_relative_from_include()}/../__modules__//ecs/cluster"
}

locals {
  global_vars      = read_terragrunt_config(find_in_parent_folders("global.hcl"))
  environment_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  product_name = local.global_vars.locals.product_name
  environment  = local.environment_vars.locals.environment
}

dependency "vpc" {
  config_path = find_in_parent_folders("vpc")
  mock_outputs = {
    vpc_id                      = "vpc-mock"
    public_subnets              = ["subnet-mock1", "subnet-mock2"]
    private_subnets_cidr_blocks = ["10.0.3.0/24", "10.0.4.0/24"]
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]
}

inputs = {
  cluster_name                           = "${local.product_name}-${local.environment}"
  vpc_id                                 = dependency.vpc.outputs.vpc_id
  public_subnets                         = dependency.vpc.outputs.public_subnets
  private_subnets_cidr_blocks            = dependency.vpc.outputs.private_subnets_cidr_blocks
  containerInsights                      = "enabled"
  cloudwatch_log_group_retention_in_days = 14
}
