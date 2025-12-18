# Copenhagen AI Hackathon Helm Chart

Helm chart for deploying the Copenhagen AI Hackathon consultant matching application to Kubernetes.

## Components

- **Frontend**: React application served by Nginx
- **Backend**: Python FastAPI application
- **Weaviate**: Vector database for semantic search

## Prerequisites

- Kubernetes cluster with Traefik ingress controller
- cert-manager for TLS certificates
- Image pull secret for GHCR (ghcr-pull-secret)
- OpenAI API key

## Installation

### 1. Create namespace

```bash
kubectl create namespace copenhagen-ai-hackathon
```

### 2. Copy image pull secret

```bash
kubectl get secret ghcr-pull-secret -n fullstack -o yaml | \
  sed 's/namespace: fullstack/namespace: copenhagen-ai-hackathon/' | \
  kubectl apply -f -
```

### 3. Create application secrets

```bash
kubectl create secret generic copenhagen-ai-hackathon-secrets \
  --from-literal=openai-api-key=<YOUR_OPENAI_API_KEY> \
  --namespace=copenhagen-ai-hackathon
```

### 4. Install the chart

```bash
helm install copenhagen-ai-hackathon ./charts/copenhagen-ai-hackathon \
  --namespace copenhagen-ai-hackathon
```

## Configuration

See `values.yaml` for all configuration options.

### Key Values

- `frontend.image.repository`: Frontend Docker image
- `backend.image.repository`: Backend Docker image
- `weaviate.enabled`: Enable/disable Weaviate deployment
- `ingress.host`: Application hostname
- `backend.env.OPENAI_APIKEY`: Set via secrets (see above)

## Accessing the Application

Once deployed, access at:
- **Application**: https://copenhagen-ai-hackathon.w.vibeoholic.com
- **API Docs**: https://copenhagen-ai-hackathon.w.vibeoholic.com/docs

## Monitoring

Check deployment status:

```bash
kubectl get pods -n copenhagen-ai-hackathon
kubectl get ingress -n copenhagen-ai-hackathon
kubectl logs -n copenhagen-ai-hackathon -l component=backend
```

## Uninstallation

```bash
helm uninstall copenhagen-ai-hackathon --namespace copenhagen-ai-hackathon
kubectl delete namespace copenhagen-ai-hackathon
```
