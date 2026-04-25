terraform {
  source = "../../../__modules__//kms"
}

include "root" {
  path = find_in_parent_folders("root.hcl")
}

inputs = {
  alias = "alias/deployment-key"
}
