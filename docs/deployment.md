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
