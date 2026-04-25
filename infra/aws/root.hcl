#==============================================================================
# TERRAGRUNT CONFIGURATION
#==============================================================================

locals {
  global_vars      = try(read_terragrunt_config(find_in_parent_folders("global.hcl")), null)
  region_vars      = try(read_terragrunt_config(find_in_parent_folders("region.hcl")), null)
  account_vars     = try(read_terragrunt_config(find_in_parent_folders("account.hcl")), null)
  environment_vars = try(read_terragrunt_config(find_in_parent_folders("env.hcl")), null)

  product_name = try(local.global_vars.locals.product_name, null)
  environment  = try(local.environment_vars.locals.environment, null)
  account_name = try(local.account_vars.locals.account_name, null)
  account_id   = try(local.account_vars.locals.aws_account_id, null)
  aws_profile  = try(local.account_vars.locals.aws_profile, null)
  aws_region   = try(local.region_vars.locals.aws_region, "ap-southeast-1")
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF

terraform {
  required_version = ">= 1.9.8"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.87"
    }
  }
}

provider "aws" {
  region              = "${local.aws_region}"
  allowed_account_ids = ["${local.account_id}"]
  profile             = "${local.aws_profile}"
}
EOF
}

remote_state {
  backend = "s3"
  config = {
    encrypt        = true
    bucket         = "${local.product_name}-tf-state-${local.aws_region}"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = local.aws_region
    dynamodb_table = "terraform-locks"
    profile        = local.aws_profile
  }
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}

inputs = merge(
  {
    tags = {
      Product     = local.product_name
      Environment = local.environment
      Terraform   = "true"
    }
  }
)
