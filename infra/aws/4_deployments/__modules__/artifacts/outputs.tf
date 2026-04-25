output "s3_bucket_id" {
  description = "The name of the bucket"
  value       = module.artifact_bucket.s3_bucket_id
}

output "s3_bucket_arn" {
  description = "The ARN of the bucket"
  value       = module.artifact_bucket.s3_bucket_arn
}
