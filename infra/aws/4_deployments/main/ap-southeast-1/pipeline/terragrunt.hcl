terraform {
  source = "../../../__modules__//codepipeline_deploy_ecs"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
}

dependency "kms" {
  config_path = "../kms"
  mock_outputs = {
    key_arn = "arn:aws:kms:ap-southeast-1:000000000000:key/mock"
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]
}

dependency "artifacts" {
  config_path = "../artifacts"
  mock_outputs = {
    s3_bucket_id  = "mock-bucket"
    s3_bucket_arn = "arn:aws:s3:::mock-bucket"
  }
  mock_outputs_allowed_terraform_commands = ["validate", "plan", "init"]
}

locals {
  global_vars  = read_terragrunt_config(find_in_parent_folders("global.hcl"))
  region_vars  = read_terragrunt_config(find_in_parent_folders("region.hcl"))
  product_name = local.global_vars.locals.product_name
  aws_region   = local.region_vars.locals.aws_region
}

inputs = {
  name = "${local.product_name}-release"

  codestar_connection_arn = "arn:aws:codeconnections:ap-southeast-1:536322508586:connection/f31c55cc-0b27-46a2-a7eb-906855d9cb84"

  github_owner = "chuong321"
  github_repo  = "PBL5-"
  branch       = "main"

  build_config = {
    buildspec = file("${get_terragrunt_dir()}/../../../__templates__/build_test_python.yml")
  }

  artifact_buckets = {
    (local.aws_region) = {
      bucket_id      = dependency.artifacts.outputs.s3_bucket_id
      bucket_arn     = dependency.artifacts.outputs.s3_bucket_arn
      encryption_key = dependency.kms.outputs.key_arn
    }
  }
  artifact_encryption_key = dependency.kms.outputs.key_arn
}
