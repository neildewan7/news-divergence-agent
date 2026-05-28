# Deployment Guide

Live URL: https://news-divergence-agent-314861703491.us-central1.run.app

## Prerequisites

- Python 3.12
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud` CLI)
- Access to GCP project `news-divergence-project` (ask Neil or Clara to invite you)
- The `.env` file (never committed — get it from a teammate directly)

## Local development

```bash
# Clone and enter the repo
git clone https://github.com/neildewan7/news-divergence-agent.git
cd news-divergence-agent

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add the .env file (get from teammate — never commit this)
# Required keys: ELASTICSEARCH_API_KEY, ELASTICSEARCH_ENDPOINT, MCP_ENDPOINT

# Authenticate with Google Cloud (needed for Vertex AI / Gemini)
gcloud auth application-default login

# Run the CLI agent (local test, prints to terminal)
python src/agent.py

# Run the Flask server locally
python src/app.py
# Server starts at http://localhost:8080
```

## Test the running server

```bash
# Health check
curl http://localhost:8080/health
# → {"status": "ok"}

# Agent query
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Libya Derna floods September 2023"}'
```

Replace `localhost:8080` with the live URL to test the deployed version.

## Deploy to Cloud Run

Only needed when you want to push a new version. Build and push the image, then deploy.

### One-time setup (already done — skip if repo/APIs exist)

```bash
# Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  --project=news-divergence-project

# Create Artifact Registry repo
gcloud artifacts repositories create news-divergence-repo \
  --repository-format=docker --location=us-central1 --project=news-divergence-project

# Grant Vertex AI access to the Cloud Run service account
# Get project number first:
gcloud projects describe news-divergence-project --format="value(projectNumber)"
# Then substitute PROJECT_NUMBER below:
gcloud projects add-iam-policy-binding news-divergence-project \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### Build and push image

```bash
gcloud builds submit \
  --tag us-central1-docker.pkg.dev/news-divergence-project/news-divergence-repo/news-divergence-agent:latest \
  --project=news-divergence-project \
  .
```

Run from the repo root. Cloud Build uploads the source and builds the image remotely — no local Docker needed.

### Deploy

```bash
gcloud run deploy news-divergence-agent \
  --image=us-central1-docker.pkg.dev/news-divergence-project/news-divergence-repo/news-divergence-agent:latest \
  --region=us-central1 \
  --project=news-divergence-project \
  --allow-unauthenticated \
  --set-env-vars="MCP_ENDPOINT=<value from .env>,ELASTICSEARCH_API_KEY=<value from .env>"
```

The service URL prints at the end. No `GOOGLE_API_KEY` needed — Vertex AI authenticates
via the Cloud Run service account automatically.

### Get the live URL at any time

```bash
gcloud run services describe news-divergence-agent \
  --region=us-central1 --project=news-divergence-project \
  --format="value(status.url)"
```

## Utility scripts

```bash
# Re-index synthetic fallback articles into Elastic (Libya/Derna demo case)
python scripts/index_test_data.py

# Probe GDELT coverage for the demo event (run before changing demo case)
python scripts/test_gdelt.py

# Run GDELT pipeline manually to pre-warm the index
python -c "
import sys; sys.path.insert(0, 'scripts')
from gdelt_pipeline import populate_index_for_query
populate_index_for_query('Derna AND flood AND Libya',
                         start_date='2023-09-08', end_date='2023-10-10')
"

# Smoke test: MCP connection only
python scripts/test_mcp.py

# Smoke test: MCP + Gemini connectivity
python scripts/agent_test.py
```

> **Note on dependencies**: `trafilatura` requires `lxml_html_clean` (listed in
> requirements.txt). If you see an `ImportError` about `lxml.html.clean`, run
> `pip install lxml_html_clean`.

## Environment variables

| Variable | Where used | How to get |
|---|---|---|
| `ELASTICSEARCH_API_KEY` | Elastic auth | Elastic Cloud console → API Keys |
| `ELASTICSEARCH_ENDPOINT` | index_test_data.py | Elastic Cloud console → Endpoints |
| `MCP_ENDPOINT` | Agent MCP connection | Elastic Agent Builder → MCP endpoint |
