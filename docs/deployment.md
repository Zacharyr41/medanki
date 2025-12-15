# Deployment Guide

## Docker Deployment

### Building the Image

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "medanki_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run

```bash
# Build the image
docker build -t medanki:latest .

# Run the container
docker run -p 8000:8000 medanki:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=/data/medanki.db
      - LOG_LEVEL=INFO
    volumes:
      - medanki-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api
    environment:
      - API_URL=http://api:8000

volumes:
  medanki-data:
```

Start services:
```bash
docker compose up -d
```

## Cloud Run Deployment

### Prerequisites

- Google Cloud SDK installed
- Project configured: `gcloud config set project YOUR_PROJECT`
- Cloud Run API enabled

### Deploy to Cloud Run

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT/medanki

# Deploy to Cloud Run
gcloud run deploy medanki \
  --image gcr.io/YOUR_PROJECT/medanki \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10
```

### Cloud Run Configuration

```yaml
# service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: medanki
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
        - image: gcr.io/YOUR_PROJECT/medanki
          ports:
            - containerPort: 8000
          resources:
            limits:
              cpu: "1"
              memory: "1Gi"
          env:
            - name: LOG_LEVEL
              value: "INFO"
```

Deploy with:
```bash
gcloud run services replace service.yaml
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `./medanki.db` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` |
| `MAX_UPLOAD_SIZE` | Maximum upload size in bytes | `10485760` (10MB) |
| `CHUNK_SIZE` | Default chunk size in tokens | `512` |
| `CHUNK_OVERLAP` | Default chunk overlap in tokens | `75` |

### Setting Environment Variables

**Docker:**
```bash
docker run -e LOG_LEVEL=DEBUG -e DATABASE_URL=/data/db.sqlite medanki:latest
```

**Cloud Run:**
```bash
gcloud run services update medanki --set-env-vars LOG_LEVEL=DEBUG
```

## Scaling Considerations

### Horizontal Scaling

MedAnki is stateless and scales horizontally. Consider:

1. **Database**: Move from SQLite to PostgreSQL for production
   ```python
   # Use async PostgreSQL
   DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   ```

2. **Vector Store**: Use managed vector database (Pinecone, Weaviate)

3. **File Storage**: Use cloud storage (GCS, S3) for uploaded documents

### Resource Requirements

| Load Level | CPU | Memory | Instances |
|------------|-----|--------|-----------|
| Development | 0.5 | 512MB | 1 |
| Light (< 100 users) | 1 | 1GB | 1-2 |
| Medium (100-1000) | 2 | 2GB | 2-5 |
| Heavy (1000+) | 2+ | 4GB+ | 5-10+ |

### Performance Tuning

1. **Connection Pooling**: Configure database connection pool size
2. **Caching**: Add Redis for session and query caching
3. **CDN**: Serve static assets via CDN
4. **Rate Limiting**: Implement rate limiting for API endpoints

## Monitoring

### Health Checks

```bash
# Liveness probe
curl http://localhost:8000/health

# Deep health check (verify database)
curl http://localhost:8000/health/deep
```

### Logging

Structured JSON logging in production:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })
```

### Metrics

Export Prometheus metrics:
```bash
# Add to requirements
prometheus-fastapi-instrumentator

# In main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

## Security

### Production Checklist

- [ ] Enable HTTPS (TLS termination at load balancer)
- [ ] Configure CORS properly (not `*` in production)
- [ ] Set secure headers (HSTS, CSP, X-Frame-Options)
- [ ] Rate limit API endpoints
- [ ] Validate and sanitize all inputs
- [ ] Use secrets management for credentials
- [ ] Enable audit logging
- [ ] Regular dependency updates

### Secrets Management

Use environment variables or secret managers:

```bash
# Google Secret Manager
gcloud secrets create medanki-db-password --data-file=-

# Reference in Cloud Run
gcloud run services update medanki \
  --set-secrets=DATABASE_PASSWORD=medanki-db-password:latest
```

## Complete GCP Deployment Guide

This section provides step-by-step instructions to deploy MedAnki to Google Cloud Platform.

### Prerequisites

```bash
# Install Google Cloud SDK
# macOS:
brew install google-cloud-sdk

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Step 1: Store Secrets in Secret Manager

```bash
# Store your Anthropic API key
echo -n "sk-ant-api03-xxxxx" | gcloud secrets create anthropic-api-key --data-file=-

# Grant Cloud Run access to the secret
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 2: Create Dockerfiles

**API Dockerfile** (`Dockerfile.api`):
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
COPY data/ ./data/

# Install dependencies
RUN uv sync --frozen --no-dev

# Expose port
EXPOSE 8080

# Cloud Run expects port 8080
CMD ["uv", "run", "uvicorn", "medanki_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Frontend Dockerfile** (`web/Dockerfile`):
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
```

**Frontend nginx.conf** (`web/nginx.conf`):
```nginx
server {
    listen 8080;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass ${API_URL};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Step 3: Deploy Weaviate (Vector Database)

**Option A: Cloud Run (Recommended for simplicity)**
```bash
# Deploy Weaviate to Cloud Run
gcloud run deploy medanki-weaviate \
  --image semitechnologies/weaviate:1.28.0 \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 1 \
  --set-env-vars="AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true,PERSISTENCE_DATA_PATH=/data,DEFAULT_VECTORIZER_MODULE=none" \
  --allow-unauthenticated

# Get the URL
WEAVIATE_URL=$(gcloud run services describe medanki-weaviate --region us-central1 --format='value(status.url)')
echo "Weaviate URL: $WEAVIATE_URL"
```

**Option B: Compute Engine (For persistent storage)**
```bash
# Create a VM with persistent disk
gcloud compute instances create medanki-weaviate \
  --machine-type e2-standard-2 \
  --zone us-central1-a \
  --boot-disk-size 50GB \
  --image-family cos-stable \
  --image-project cos-cloud \
  --metadata startup-script='#!/bin/bash
docker run -d \
  --name weaviate \
  -p 8080:8080 \
  -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
  -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
  -v /home/weaviate-data:/var/lib/weaviate \
  semitechnologies/weaviate:1.28.0'

# Get external IP
WEAVIATE_IP=$(gcloud compute instances describe medanki-weaviate --zone us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')
echo "Weaviate IP: http://$WEAVIATE_IP:8080"
```

### Step 4: Deploy API Backend

```bash
# Build and push API image
gcloud builds submit --tag gcr.io/$PROJECT_ID/medanki-api -f Dockerfile.api .

# Deploy API to Cloud Run with secrets
gcloud run deploy medanki-api \
  --image gcr.io/$PROJECT_ID/medanki-api \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest \
  --set-env-vars="WEAVIATE_URL=$WEAVIATE_URL,LOG_LEVEL=INFO" \
  --allow-unauthenticated

# Get the API URL
API_URL=$(gcloud run services describe medanki-api --region us-central1 --format='value(status.url)')
echo "API URL: $API_URL"
```

### Step 5: Deploy Frontend

**Option A: Firebase Hosting (Recommended)**
```bash
cd web

# Install Firebase CLI
npm install -g firebase-tools

# Login and initialize
firebase login
firebase init hosting  # Select your project, use 'dist' as public dir

# Create .env.production
echo "VITE_API_URL=$API_URL" > .env.production

# Build and deploy
npm run build
firebase deploy --only hosting

# Get the URL (typically https://YOUR_PROJECT.web.app)
```

**Option B: Cloud Run**
```bash
cd web

# Update API URL in build
echo "VITE_API_URL=$API_URL" > .env.production
npm run build

# Build and push frontend image
gcloud builds submit --tag gcr.io/$PROJECT_ID/medanki-web .

# Deploy frontend
gcloud run deploy medanki-web \
  --image gcr.io/$PROJECT_ID/medanki-web \
  --platform managed \
  --region us-central1 \
  --memory 256Mi \
  --cpu 1 \
  --allow-unauthenticated

# Get the frontend URL
WEB_URL=$(gcloud run services describe medanki-web --region us-central1 --format='value(status.url)')
echo "Frontend URL: $WEB_URL"
```

### Step 6: Configure CORS (Important!)

Update your API to allow the frontend domain:

```bash
# Update API with correct CORS origin
gcloud run services update medanki-api \
  --region us-central1 \
  --set-env-vars="CORS_ORIGINS=$WEB_URL"
```

### Step 7: Custom Domain (Optional)

```bash
# Map a custom domain to Cloud Run
gcloud run domain-mappings create \
  --service medanki-web \
  --region us-central1 \
  --domain medanki.yourdomain.com

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain medanki.yourdomain.com \
  --region us-central1
```

### Deployment Summary

After completing these steps, you'll have:

| Service | URL Pattern |
|---------|-------------|
| **Frontend** | `https://YOUR_PROJECT.web.app` (Firebase) or `https://medanki-web-xxxxx.run.app` (Cloud Run) |
| **API** | `https://medanki-api-xxxxx.run.app` |
| **Weaviate** | `https://medanki-weaviate-xxxxx.run.app` (internal) |

### Cost Estimation

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| Cloud Run API (light usage) | $5-20 |
| Cloud Run Weaviate | $30-50 |
| Firebase Hosting | Free tier |
| Secret Manager | < $1 |
| **Total** | **~$35-70/month** |

### Troubleshooting

**Check Cloud Run logs:**
```bash
gcloud run services logs read medanki-api --region us-central1 --limit 100
```

**Test API health:**
```bash
curl $API_URL/health
```

**Test Weaviate connection:**
```bash
curl $WEAVIATE_URL/v1/.well-known/ready
```

**View secrets:**
```bash
gcloud secrets versions access latest --secret=anthropic-api-key
```
