variable "bucket_name" {
  description = "Globally-unique S3 bucket name for processed CSV files."
  type        = string
  default     = "CHANGEME-spidersilk-processed-files"
}

variable "aws_region" {
  description = "AWS region to create the bucket in."
  type        = string
  default     = "us-east-1"
}

variable "glacier_transition_days" {
  description = "Days after upload before an object transitions to S3 Glacier."
  type        = number
  default     = 30
}

variable "noncurrent_version_expiration_days" {
  description = "Days before noncurrent object versions are permanently deleted."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
  default = {
    Project   = "spidersilk"
    ManagedBy = "terraform"
  }
}
