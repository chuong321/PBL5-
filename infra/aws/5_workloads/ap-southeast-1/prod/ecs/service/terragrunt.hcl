include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "envcommon" {
  path = "../../../../__shared__/ecs_service.hcl"
}

inputs = {
  cpu           = 512
  memory        = 1024
  desired_count = 1

  environment_variables = [
    {
      name  = "DEBUG"
      value = "false"
    }
  ]
}
