# Staging Bootstrap Procedure

1. **Provision cloud resources**
   ```bash
   cd infra/terraform/public
   terraform init
   terraform apply
   ```
   Outputs include the ALB DNS name and ECR repository URL.

2. **Publish container image**
   ```bash
   export IMAGE=$(terraform output -raw ecr_repository_url):$(git rev-parse --short HEAD)
   docker build -t "$IMAGE" .
   docker push "$IMAGE"
   ```

3. **Deploy via Helm**
   ```bash
   helm upgrade --install cd-collector ./deploy/helm/cd-collector \
     --namespace cd-collector \
     --create-namespace \
     --set image.repository=$(terraform output -raw ecr_repository_url) \
     --set image.tag=$(git rev-parse --short HEAD) \
     --set ingress.hosts[0].host=staging.app.example.com \
     --set ingress.tls[0].hosts[0]=staging.app.example.com
   ```

4. **Smoke test**
   ```bash
   curl -H "Host: staging.app.example.com" https://staging.app.example.com/readyz
   ```

5. **Synthetic monitoring**
   Configure the uptime monitor to hit `/healthz` and `/readyz` at 1-minute intervals; tie alerts to PagerDuty as described in the observability runbook.
