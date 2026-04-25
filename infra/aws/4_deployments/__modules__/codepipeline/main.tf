data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

#==============================================================================
# CodePipeline
#==============================================================================

resource "aws_codepipeline" "this" {
  name     = var.name
  role_arn = aws_iam_role.codepipeline.arn

  dynamic "artifact_store" {
    for_each = var.artifact_buckets

    content {
      type     = "S3"
      location = artifact_store.value.bucket_id

      encryption_key {
        id   = try(artifact_store.value.encryption_key, var.artifact_encryption_key)
        type = "KMS"
      }
    }
  }

  dynamic "stage" {
    for_each = [for s in var.stages : {
      name   = s.name
      action = s.action
    } if(lookup(s, "enabled", true))]

    content {
      name = stage.value.name

      dynamic "action" {
        for_each = stage.value.action

        content {
          name             = action.value["name"]
          owner            = action.value["owner"]
          version          = action.value["version"]
          category         = action.value["category"]
          provider         = action.value["provider"]
          input_artifacts  = lookup(action.value, "input_artifacts", [])
          output_artifacts = lookup(action.value, "output_artifacts", [])
          configuration    = lookup(action.value, "configuration", {})
          run_order        = lookup(action.value, "run_order", null)
          region           = lookup(action.value, "region", data.aws_region.current.name)
        }
      }
    }
  }
}

#==============================================================================
# IAM
#==============================================================================

data "aws_iam_policy_document" "codepipeline_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }
    effect = "Allow"
  }
}

resource "aws_iam_role" "codepipeline" {
  name               = "${var.name}-codepipeline"
  assume_role_policy = data.aws_iam_policy_document.codepipeline_assume_role.json
}

locals {
  codebuild_projects = flatten([
    for s in var.stages : [
      for a in s.action : a.configuration["ProjectName"]
      if lookup(s, "enabled", true) && a.category == "Build" && a.provider == "CodeBuild" && lookup(a.configuration, "ProjectName", null) != null
    ]
  ])
}

data "aws_iam_policy_document" "codepipeline" {
  statement {
    sid = "CodePipelineDefault"
    actions = [
      "elasticloadbalancing:*",
      "autoscaling:*",
      "cloudwatch:*",
      "s3:*",
      "sns:*",
      "ecs:*",
      "iam:PassRole",
    ]
    resources = ["*"]
    effect    = "Allow"
  }

  statement {
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
  }

  statement {
    sid = "KMSArtifacts"
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey",
    ]
    resources = distinct(compact(concat(
      [var.artifact_encryption_key],
      [for bucket in values(var.artifact_buckets) : bucket.encryption_key if bucket.encryption_key != null]
    )))
  }

  statement {
    sid       = "Codestar"
    actions   = ["codestar-connections:UseConnection"]
    resources = [var.codestar_connection_arn]
    effect    = "Allow"
  }

  dynamic "statement" {
    for_each = length(local.codebuild_projects) > 0 ? [1] : []

    content {
      sid    = "CodeBuild"
      effect = "Allow"
      actions = [
        "codebuild:BatchGetBuilds",
        "codebuild:StartBuild",
        "codebuild:BatchGetBuildBatches",
        "codebuild:StartBuildBatch"
      ]
      resources = [
        for project in local.codebuild_projects :
        format("arn:aws:codebuild:%s:%s:project/%s", data.aws_region.current.name, data.aws_caller_identity.current.account_id, project)
      ]
    }
  }
}

resource "aws_iam_policy" "codepipeline" {
  name   = "${var.name}-codepipeline"
  policy = data.aws_iam_policy_document.codepipeline.json
}

resource "aws_iam_role_policy_attachment" "codepipeline" {
  role       = aws_iam_role.codepipeline.id
  policy_arn = aws_iam_policy.codepipeline.arn
}

resource "aws_kms_grant" "codepipeline" {
  name              = "${var.name}-codepipeline"
  key_id            = var.artifact_encryption_key
  grantee_principal = aws_iam_role.codepipeline.arn
  operations        = ["Encrypt", "Decrypt", "GenerateDataKey"]
}
