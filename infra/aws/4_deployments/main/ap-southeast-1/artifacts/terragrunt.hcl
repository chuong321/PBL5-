terraform {
  source = "../../../__modules__//artifacts"
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

inputs = {
  artifact_encryption_key = dependency.kms.outputs.key_arn
}
