module "artifact_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "3.14.1"

  bucket_prefix = "deployment-artifact-"
  acl           = "private"
  force_destroy = true

  control_object_ownership = true
  object_ownership         = "ObjectWriter"

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = var.artifact_encryption_key
        sse_algorithm     = "aws:kms"
      }
    }
  }

  tags = merge(
    { Name = "deployment-artifact-" },
    var.tags,
  )
}
