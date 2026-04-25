include "root" {
  path = find_in_parent_folders("root.hcl")
}

include "envcommon" {
  path = "../../../../__shared__/ecs_cluster.hcl"
}
