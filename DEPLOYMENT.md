# MCP Servers Deployment Guide

This guide explains how to deploy the MCP servers to Google Cloud Platform (GCP) Cloud Run using GitHub Actions.

## Prerequisites

1. **GCP Project**: You need a GCP project with billing enabled
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **GCP Service Account**: A service account with appropriate permissions

## Required GitHub Secrets

Set up the following secrets in your GitHub repository (`Settings > Secrets and variables > Actions`):

### GCP Configuration
- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_SA_KEY`: Service account JSON key (see setup below)

### Database Configuration
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key

### Google Calendar Integration
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret
- `GOOGLE_CALENDAR_WEBHOOK_URL`: Webhook URL for Google Calendar events


## GCP Service Account Setup

1. **Create a Service Account**:
   ```bash
   gcloud iam service-accounts create mcp-deployer \
     --description="Service account for MCP servers deployment" \
     --display-name="MCP Deployer"
   ```

2. **Grant Required Permissions**:
   ```bash
   # Cloud Run permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:mcp-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/run.admin"

   # Artifact Registry permissions
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:mcp-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/artifactregistry.admin"

   # Storage permissions (for container images)
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:mcp-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/storage.admin"

   # Service Account User (to deploy as service account)
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:mcp-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/iam.serviceAccountUser"
   ```

3. **Create and Download Service Account Key**:
   ```bash
   gcloud iam service-accounts keys create key.json \
     --iam-account=mcp-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Add the Key to GitHub Secrets**:
   - Copy the entire contents of `key.json`
   - Add it as the `GCP_SA_KEY` secret in GitHub

## Deployment Workflow

The GitHub workflow (`.github/workflows/deploy-gcp.yml`) automatically:

1. **Triggers on**:
   - Push to `main` branch only

2. **Builds and Deploys**:
   - The `google-calendar` server
   - Creates Docker image using the Dockerfile
   - Pushes image to Google Artifact Registry
   - Deploys to Cloud Run with appropriate configuration

3. **Configuration**:
   - **Memory**: 1GB per instance
   - **CPU**: 1 vCPU per instance
   - **Scaling**: 0-10 instances (auto-scaling)
   - **Port**: 8000
   - **Authentication**: Allows unauthenticated requests

## Manual Deployment

You can also deploy manually using the gcloud CLI:

### Build and Push Images
```bash
# Set variables
PROJECT_ID="your-project-id"
REGION="us-central1"

# Build and push google-calendar server
docker build -f servers/google-calendar/Dockerfile -t gcr.io/$PROJECT_ID/mcp-google-calendar .
docker push gcr.io/$PROJECT_ID/mcp-google-calendar

```

### Deploy to Cloud Run
```bash
# Deploy google-calendar server
gcloud run deploy mcp-google-calendar \
  --image gcr.io/$PROJECT_ID/mcp-google-calendar \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10

```

## Environment Variables

The deployment automatically sets the following environment variables:

- `ENVIRONMENT=production`
- All secrets are mounted as environment variables

## Monitoring and Logs

1. **View Services**:
   ```bash
   gcloud run services list --region=us-central1
   ```

2. **View Logs**:
   ```bash
   # Google Calendar server logs
   gcloud logs tail --follow --filter="resource.labels.service_name=mcp-google-calendar"

   ```

3. **Service URLs**:
   After deployment, you can get the service URLs:
   ```bash
   gcloud run services describe mcp-google-calendar --region=us-central1 --format='value(status.url)'
   ```

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure your service account has all required IAM roles
2. **Build Failures**: Check that all dependencies are properly defined in pyproject.toml
3. **Runtime Errors**: Check Cloud Run logs for detailed error messages

### Health Checks

The workflow includes basic health checks. You can also manually test:

```bash
# Test the deployed services
curl https://your-service-url/health
```

## Cost Optimization

- **Auto-scaling**: Services scale to 0 when not in use
- **Resource Limits**: Memory and CPU are optimized for the workload
- **Regional Deployment**: Using us-central1 for cost efficiency

## Security

- Services use Google-managed SSL certificates
- Environment variables are securely managed through Google Secret Manager
- Service account follows principle of least privilege
