data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

#==============================================================================
# IAM Role
#==============================================================================

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
    effect = "Allow"
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-codebuild"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

data "aws_iam_policy_document" "this" {
  statement {
    sid = "CloudWatchLogs"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["*"]
    effect    = "Allow"
  }

  statement {
    sid = "ECRAuth"
    actions = [
      "ecr:GetAuthorizationToken",
    ]
    resources = ["*"]
    effect    = "Allow"
  }

  statement {
    sid = "ECRPushPull"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart",
    ]
    resources = ["*"]
    effect    = "Allow"
  }

  dynamic "statement" {
    for_each = var.codebuild_iam_role_statements

    content {
      sid       = try(statement.value.sid, null)
      actions   = try(statement.value.actions, null)
      resources = try(statement.value.resources, null)
      effect    = try(statement.value.effect, "Allow")

      dynamic "condition" {
        for_each = try([statement.value.condition], [])

        content {
          test     = condition.value.test
          variable = condition.value.variable
          values   = condition.value.values
        }
      }
    }
  }
}

resource "aws_iam_policy" "this" {
  name   = "${var.name}-codebuild"
  policy = data.aws_iam_policy_document.this.json
}

resource "aws_iam_role_policy_attachment" "this" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this.arn
}

#==============================================================================
# CodeBuild Project
#==============================================================================

resource "aws_codebuild_project" "this" {
  name           = var.name
  build_timeout  = var.build_timeout
  encryption_key = var.encryption_key

  service_role = aws_iam_role.this.arn

  artifacts {
    type = var.artifact_type
  }

  environment {
    compute_type                = var.build_compute_type
    image                       = var.build_image
    type                        = "LINUX_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    dynamic "environment_variable" {
      for_each = var.environment_variables

      content {
        name  = environment_variable.value.name
        value = environment_variable.value.value
        type  = try(environment_variable.value.type, "PLAINTEXT")
      }
    }
  }

  source {
    type      = var.source_type
    buildspec = var.buildspec
  }

  dynamic "cache" {
    for_each = var.cache_type != "NO_CACHE" ? [1] : []

    content {
      type  = var.cache_type
      modes = var.local_cache_modes
    }
  }

  logs_config {
    cloudwatch_logs {
      status = "ENABLED"
    }
  }

  tags = merge(
    { Name = "${var.name}-codebuild" },
    var.tags,
  )
}

resource "aws_kms_grant" "this" {
  count = var.encryption_key != null ? 1 : 0

  name              = "${var.name}-codebuild"
  key_id            = var.encryption_key
  grantee_principal = aws_iam_role.this.arn
  operations        = ["Encrypt", "Decrypt", "GenerateDataKey"]
}
