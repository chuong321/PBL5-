data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  github_repository = "${var.github_owner}/${var.github_repo}"
}

#==============================================================================
# CodeBuild - Build & Test
#==============================================================================

module "codebuild_test" {
  source = "../codebuild"

  name              = "${var.name}-build-test"
  buildspec         = var.build_config.buildspec
  cache_type        = "LOCAL"
  local_cache_modes = ["LOCAL_CUSTOM_CACHE"]
  encryption_key    = var.artifact_encryption_key

  environment_variables = var.build_config.environment_variables

  codebuild_iam_role_statements = [
    {
      sid = "S3Artifacts"
      actions = [
        "s3:Get*",
        "s3:List*",
        "s3:PutObject"
      ]
      resources = flatten([
        for bucket in values(var.artifact_buckets) : [
          bucket.bucket_arn,
          "${bucket.bucket_arn}/*"
        ]
      ])
      effect = "Allow"
    },
    {
      sid       = "Codestar"
      actions   = ["codestar-connections:UseConnection"]
      resources = [var.codestar_connection_arn]
      effect    = "Allow"
    }
  ]

  tags = var.tags
}

#==============================================================================
# CodePipeline - Source -> Build & Test (no Docker build - model files are local only)
#==============================================================================

module "codepipeline" {
  source = "../codepipeline"

  name                    = var.name
  artifact_buckets        = var.artifact_buckets
  artifact_encryption_key = var.artifact_encryption_key
  codestar_connection_arn = var.codestar_connection_arn
  codestar_repository_id  = local.github_repository

  stages = [
    {
      name = "Source"
      action = [{
        name             = "Source"
        category         = "Source"
        owner            = "AWS"
        provider         = "CodeStarSourceConnection"
        version          = "1"
        output_artifacts = ["SourceArtifact"]

        configuration = {
          ConnectionArn        = var.codestar_connection_arn
          FullRepositoryId     = local.github_repository
          BranchName           = var.branch
          OutputArtifactFormat = "CODEBUILD_CLONE_REF"
        }
      }]
    },
    {
      name = "Build-Test"
      action = [{
        name             = "Build-Test"
        category         = "Build"
        owner            = "AWS"
        provider         = "CodeBuild"
        version          = "1"
        input_artifacts  = ["SourceArtifact"]
        output_artifacts = ["BuildTestArtifact"]

        configuration = {
          ProjectName = module.codebuild_test.project_name
        }
      }]
    }
  ]

  tags = var.tags
}
