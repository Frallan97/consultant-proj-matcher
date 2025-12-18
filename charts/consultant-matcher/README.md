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
kubectl create namespace consultant-matcher
```

### 2. Copy image pull secret

```bash
kubectl get secret ghcr-pull-secret -n fullstack -o yaml | \
  sed 's/namespace: fullstack/namespace: consultant-matcher/' | \
  kubectl apply -f -
```

### 3. Create application secrets

```bash
kubectl create secret generic consultant-matcher-secrets \
  --from-literal=openai-api-key=<YOUR_OPENAI_API_KEY> \
  --namespace=consultant-matcher
```

### 4. Install the chart

```bash
helm install consultant-matcher ./charts/consultant-matcher \
  --namespace consultant-matcher
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
- **Application**: https://consultant-matcher.w.vibeoholic.com
- **API Docs**: https://consultant-matcher.w.vibeoholic.com/docs

## Monitoring

Check deployment status:

```bash
kubectl get pods -n consultant-matcher
kubectl get ingress -n consultant-matcher
kubectl logs -n consultant-matcher -l component=backend
```

## Uninstallation

```bash
helm uninstall consultant-matcher --namespace consultant-matcher
kubectl delete namespace consultant-matcher
```
