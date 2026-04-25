resource "aws_kms_key" "this" {
  description = "KMS key for deployment artifact encryption"
}

resource "aws_kms_alias" "this" {
  count = var.alias != null ? 1 : 0

  target_key_id = aws_kms_key.this.id
  name          = var.alias
}
