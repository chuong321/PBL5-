output "project_name" {
  description = "Project name"
  value       = aws_codebuild_project.this.name
}

output "project_arn" {
  description = "Project ARN"
  value       = aws_codebuild_project.this.arn
}

output "role_arn" {
  description = "IAM Role ARN"
  value       = aws_iam_role.this.arn
}
