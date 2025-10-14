output "ecr_repository_url" {
  value       = aws_ecr_repository.this.repository_url
  description = "Container image repository URL."
}

output "secretsmanager_secret_arn" {
  value       = aws_secretsmanager_secret.app.arn
  description = "ARN of the application configuration secret."
}

output "db_endpoint" {
  value       = aws_db_instance.postgres.address
  description = "Postgres endpoint hostname."
}

output "db_port" {
  value       = aws_db_instance.postgres.port
  description = "Postgres port."
}

output "redis_primary_endpoint" {
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
  description = "Redis primary endpoint hostname."
}

output "alb_dns_name" {
  value       = aws_lb.https.dns_name
  description = "ALB DNS name for ingress."
}

output "alb_security_group_id" {
  value       = aws_security_group.alb.id
  description = "Security group ID for the ALB."
}

output "target_group_arn" {
  value       = aws_lb_target_group.https.arn
  description = "Target group ARN for Kubernetes ingress controller integration."
}
