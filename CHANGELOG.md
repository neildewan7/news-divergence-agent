# Changelog

## 2026-05-25 — Day 1 (Neil)

### Decisions
- Pivoted from GCP Agent Platform Studio to code-based Python agent. Studio's MCP
  feature doesn't support API key auth yet ("Coming soon"); Elastic requires it.
- Architecture: LangChain MCP adapter + Gemini via Vertex AI + Elastic MCP server.
  May migrate to Google ADK later for stricter hackathon compliance.
- Demo case (provisional): Kabul market explosion September 2024. 5 synthetic
  articles for initial test; real multilingual corpus TBD.

### Progress
- GCP project `news-divergence-project` created with $300 free trial
- Elastic Cloud Serverless project created with Agent Builder enabled
- $100 hackathon credit application submitted (status: pending)
- Public GitHub repo created with MIT license + .gitignore for secrets
- Elastic MCP via LangChain: working (auth confirmed)
- Gemini via ChatVertexAI (Vertex AI path, hackathon-compliant): working
- 5 synthetic articles indexed with semantic_text mapping: working
- End-to-end agent extracts divergence across sources with citations: working

### Open
- Cloud Run deployment (Stage 1 hard requirement)
- Multilingual capability untested
- Real news (vs synthetic) untested
- Structured output format (vs current prose)
- Demo video

## 2026-05-26 — Day 2 (Clara)

### Decisions
- Kept ChatVertexAI (not ChatGoogleGenerativeAI) — Vertex AI is required for
  hackathon compliance; AI Studio API would disqualify.
- Flask chosen as web server wrapper for Cloud Run (minimal, no new AI deps).
- asyncio event loop: one persistent loop in a background thread shared across
  all requests — required because gRPC channels (Vertex AI) bind to the loop
  they're created in and break if called from a different or closed loop.

### Progress
- Flask web server added (src/app.py): POST /analyze, GET /health
- Dockerfile + .dockerignore created; image builds and runs on Cloud Run
- Fixed import: create_react_agent moved back to langgraph.prebuilt (langchain.agents
  version does not exist in installed package versions)
- Fixed thought_signature leak: Gemini 2.5 returns content as a list of typed
  blocks; extract only type=text blocks before returning response
- Fixed RuntimeError (event loop is closed): replaced asyncio.run() per-request
  with run_coroutine_threadsafe() into a single persistent loop
- Cloud Run deployment live and tested:
  https://news-divergence-agent-314861703491.us-central1.run.app
- Repo reorganised: src/ for agent + app, scripts/ for utilities
- DEPLOYMENT.md added with full teammate onboarding instructions

### Open
- Real news corpus (currently 5 synthetic articles)
- Structured output format (currently prose)
- Frontend (weakest judging criterion right now)
- Multilingual capability untested
- Demo video
