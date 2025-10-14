# Terraform Infrastructure

This directory contains Terraform configuration for the public CD-Collector deployment.

## Structure

- `modules/cd_collector` – reusable module provisioning:
  - ECR repository for container images
  - Secrets Manager secret for application credentials
  - Multi-AZ Postgres instance
  - Multi-AZ Redis replication group
  - ACM certificate + validation records
  - Application Load Balancer, listener, and target group
- `public/` – environment instantiation using the module.

## Usage

1. Provide AWS credentials (e.g., via `AWS_PROFILE`).
2. Copy `infra/terraform/public/terraform.tfvars.sample` (create file) with appropriate values:
   ```hcl
   name               = "cd-collector-prod"
   region             = "us-east-1"
   vpc_id             = "vpc-1234567890abcdef"
   private_subnet_ids = ["subnet-abc", "subnet-def"]
   public_subnet_ids  = ["subnet-ghi", "subnet-jkl"]
   db_username        = "cdcollector"
   db_password        = "super-secret"
   acm_domain_name    = "app.example.com"
   route53_zone_id    = "Z0123456789ABCDEFG"
   tags               = { Environment = "prod" }
   ```
3. Initialize and review plan:
   ```bash
   cd infra/terraform/public
   terraform init
   terraform plan -out plan.out
   ```
4. Apply when ready:
   ```bash
   terraform apply plan.out
   ```

The `aws_lb_target_group.https` output connects with the Kubernetes ingress (see Helm chart).

## Providers

This module assumes AWS as the primary cloud provider. Adjust or extend resources for other clouds as needed. For staging environments, you can override instance sizes using module variables.
