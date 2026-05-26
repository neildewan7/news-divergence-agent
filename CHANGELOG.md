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
