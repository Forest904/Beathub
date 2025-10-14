variable "name" {
  description = "Deployment prefix (e.g., cd-collector-prod)."
  type        = string
}

variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "Existing VPC ID."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs."
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs."
  type        = list(string)
}

variable "db_username" {
  description = "Database admin username."
  type        = string
}

variable "db_password" {
  description = "Database admin password."
  type        = string
  sensitive   = true
}

variable "db_engine_version" {
  description = "Postgres engine version."
  type        = string
  default     = "15.5"
}

variable "cache_node_type" {
  description = "Elasticache node type."
  type        = string
  default     = "cache.t4g.small"
}

variable "acm_domain_name" {
  description = "Primary domain name for ingress."
  type        = string
}

variable "acm_validation_domains" {
  description = "Optional SANs for ACM certificate."
  type        = list(string)
  default     = []
}

variable "route53_zone_id" {
  description = "Hosted zone ID for DNS validation."
  type        = string
}

variable "tags" {
  description = "Common tags."
  type        = map(string)
  default     = {}
}
