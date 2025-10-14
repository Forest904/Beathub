terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.29"
    }
  }

  backend "s3" {
    bucket = "cd-collector-terraform-state"
    key    = "public/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.region
}

module "cd_collector" {
  source = "../modules/cd_collector"

  name                 = var.name
  region               = var.region
  vpc_id               = var.vpc_id
  private_subnet_ids   = var.private_subnet_ids
  public_subnet_ids    = var.public_subnet_ids
  db_username          = var.db_username
  db_password          = var.db_password
  db_engine_version    = var.db_engine_version
  cache_node_type      = var.cache_node_type
  acm_domain_name      = var.acm_domain_name
  acm_validation_domains = var.acm_validation_domains
  route53_zone_id      = var.route53_zone_id
  tags                 = var.tags
}

output "alb_dns_name" {
  value = module.cd_collector.alb_dns_name
}

output "ecr_repository_url" {
  value = module.cd_collector.ecr_repository_url
}
