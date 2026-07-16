terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment and point at your own state backend before applying for real.
  # backend "s3" {
  #   bucket = "spidersilk-app-terraform-state-store"
  #   key    = "spidersilk/s3.tfstate"
  #   region = "eu-west-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "processed_files" {
  bucket = var.bucket_name
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "processed_files" {
  bucket = aws_s3_bucket.processed_files.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Private by default — the app is the only writer/reader, via IAM
# (see iam-app-policy.json), not public access.
resource "aws_s3_bucket_public_access_block" "processed_files" {
  bucket                  = aws_s3_bucket.processed_files.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "processed_files" {
  bucket = aws_s3_bucket.processed_files.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Glacier transition: processed CSVs are write-once/rarely-read after
# processing, so they move to Glacier after `glacier_transition_days` to cut
# storage cost, and noncurrent versions are cleaned up after
# `noncurrent_version_expiration_days`.
resource "aws_s3_bucket_lifecycle_configuration" "processed_files" {
  bucket = aws_s3_bucket.processed_files.id

  rule {
    id     = "glacier-transition"
    status = "Enabled"

    filter {
      prefix = "processed/"
    }

    transition {
      days          = var.glacier_transition_days
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = var.glacier_transition_days
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_expiration_days
    }
  }
}
