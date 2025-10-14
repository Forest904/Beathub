# cd-collector Helm Chart

## Install

```bash
helm upgrade --install cd-collector ./cd-collector \
  --namespace cd-collector \
  --create-namespace \
  --set image.repository=ghcr.io/your-org/cd-collector \
  --set image.tag=v1.0.0 \
  --set ingress.hosts[0].host=app.example.com \
  --set ingress.tls[0].hosts[0]=app.example.com \
  --set ingress.tls[0].secretName=cd-collector-cert \
  --set secretRefs[0].name=cd-collector-secrets
```

### Secrets

Create a secret from AWS Secrets Manager values (example):
```bash
aws secretsmanager get-secret-value \
  --secret-id cd-collector-prod/app-config \
  --query SecretString \
  --output text | jq -r 'to_entries[] | "\(.key)=\(.value)"' > app.env

kubectl create secret generic cd-collector-secrets \
  --namespace cd-collector \
  --from-env-file=app.env
```

### Smoke Test

```bash
kubectl -n cd-collector get pods
curl -H "Host: app.example.com" https://app.example.com/readyz
```
