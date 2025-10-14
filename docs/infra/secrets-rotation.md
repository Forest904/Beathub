# Secrets Rotation Plan

This document explains how application secrets are managed and rotated using AWS Secrets Manager (adjust for other providers as needed).

## Automated Rotation

The Terraform module provisions an `aws_secretsmanager_secret` named `${name}/app-config`. Enable automatic rotation in production by attaching an AWS Lambda rotation function:

```hcl
resource "aws_lambda_function" "secret_rotation" {
  # Lambda implementation that refreshes Spotify/Genius credentials
}

resource "aws_secretsmanager_secret_rotation" "app" {
  secret_id           = aws_secretsmanager_secret.app.id
  rotation_lambda_arn = aws_lambda_function.secret_rotation.arn
  rotation_rules {
    automatically_after_days = 30
  }
}
```

The application uses the `cd-collector-secrets` Kubernetes secret rendered from the Secrets Manager value. Rotate by updating Secrets Manager—apps reload via rolling restart (see Helm chart instructions below).

## Manual Fallback

1. Update the Secrets Manager secret value:
   ```bash
   aws secretsmanager put-secret-value \
     --secret-id cd-collector-prod/app-config \
     --secret-string '{"SPOTIPY_CLIENT_ID":"...", "SPOTIPY_CLIENT_SECRET":"...", "GENIUS_ACCESS_TOKEN":"..."}'
   ```
2. Restart API pods to pick up new values:
   ```bash
   kubectl rollout restart deployment/cd-collector
   ```
3. Verify health:
   ```bash
   kubectl get pods -l app.kubernetes.io/name=cd-collector
   curl https://app.example.com/readyz
   ```

## CI/CD Integration

- The GitHub Actions workflow consumes the registry credentials automatically via GITHUB_TOKEN.
- Deploy pipelines should read the Secrets Manager value and render the `cd-collector-secrets` manifest (e.g., using `kubectl` + `aws secretsmanager get-secret-value`).

## Incident Playbook

If credentials are compromised:

1. Rotate secrets via AWS console or CLI.
2. Trigger `kubectl rollout restart`.
3. Invalidate cached OAuth tokens with providers if applicable.
4. Update incident runbook with lessons learned.
