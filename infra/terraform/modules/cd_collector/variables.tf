variable "name" {
  description = "Base name prefix for all created resources."
  type        = string
}

variable "region" {
  description = "AWS region to deploy resources into."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC ID where database/cache and load balancer will live."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for database/cache."
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for load balancer ingress."
  type        = list(string)
}

variable "db_username" {
  description = "Username for Postgres database."
  type        = string
}

variable "db_password" {
  description = "Password for Postgres database."
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
  description = "Fully qualified domain name for HTTPS certificate."
  type        = string
}

variable "acm_validation_domains" {
  description = "Additional domains for ACM validation (e.g., SANs)."
  type        = list(string)
  default     = []
}

variable "route53_zone_id" {
  description = "Hosted zone ID for creating DNS validation records."
  type        = string
}

variable "tags" {
  description = "Common tags applied to resources."
  type        = map(string)
  default     = {}
}
