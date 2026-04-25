terraform {
  source = "${path_relative_from_include()}/../__modules__//ecs/service"
}

locals {
  global_vars      = read_terragrunt_config(find_in_parent_folders("global.hcl"))
  environment_vars = read_terragrunt_config(find_in_parent_folders("env.hcl"))

  product_name    = local.global_vars.locals.product_name
  environment     = local.environment_vars.locals.environment
  main_account_id = local.global_vars.locals.aws_accounts.main.account_id
  aws_region      = local.global_vars.locals.aws_accounts.main.aws_region
}

dependency "vpc" {
  config_path = find_in_parent_folders("vpc")
  mock_outputs = {
    vpc_id          = "vpc-mock"
    private_subnets = ["subnet-mock1", "subnet-mock2"]
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]
}

dependency "ecs_cluster" {
  config_path = find_in_parent_folders("cluster")
  mock_outputs = {
    cluster_arn              = "arn:aws:ecs:ap-southeast-1:000000000000:cluster/mock"
    alb_sg_security_group_id = "sg-mock"
    default_target_group_arn = "arn:aws:elasticloadbalancing:ap-southeast-1:000000000000:targetgroup/mock/mock"
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]
}

inputs = {
  name                  = "${local.product_name}-${local.environment}-app"
  cluster_arn           = dependency.ecs_cluster.outputs.cluster_arn
  vpc_id                = dependency.vpc.outputs.vpc_id
  subnet_ids            = dependency.vpc.outputs.private_subnets
  alb_security_group_id = dependency.ecs_cluster.outputs.alb_sg_security_group_id
  target_group_arn      = dependency.ecs_cluster.outputs.default_target_group_arn
  container_name        = "trash-classification"
  container_image       = "${local.main_account_id}.dkr.ecr.${local.aws_region}.amazonaws.com/${local.product_name}:latest"
  container_port        = 8000
  cpu                   = 512
  memory                = 1024
  desired_count         = 1
}
