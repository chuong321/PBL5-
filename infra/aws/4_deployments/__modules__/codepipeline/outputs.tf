output "codepipeline_id" {
  value = aws_codepipeline.this.id
}

output "codepipeline_arn" {
  value = aws_codepipeline.this.arn
}

output "codepipeline_role_arn" {
  value = aws_iam_role.codepipeline.arn
}
