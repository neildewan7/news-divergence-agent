# Working Conventions

## Stack
- Model: Gemini (latest available), accessed via Vertex AI (ChatVertexAI)
- Orchestration: LangChain MCP adapter + LangGraph ReAct agent
- Tool integration: Elastic MCP server
- Hosting target: Google Cloud Run
- Embeddings: Elastic in-cluster `multilingual-e5-small` via `semantic_text`
  (not Vertex AI — keeps embeddings inside the Elastic partner-track surface)
- Frontend: minimal single-page UI (plain HTML or React, TBD)

## Hackathon constraints
- No OpenAI, no Anthropic, no third-party LLMs in the deployed agent
- No tools that compete with Elastic (search/database) or Google Cloud
- All code newly written May 5 – June 11 2026
- Deadline: June 11 2026, 2:00 PM PT — hard cutoff

## Code conventions
- Language: Python
- Secrets: never committed; use .env + .gitignore
- Dependencies: track in requirements.txt
- Debug flag: keep DEBUG = False in src/app.py (production); src/agent.py may be
  True locally for tracing

## GDELT API conventions
- **Never use gdeltdoc Filters for keyword queries.** The library wraps multi-word
  strings in double quotes (exact phrase match), which returns near-zero results
  for historical events. Always use direct `requests.get()` with `AND`-separated
  keyword strings (e.g. `"Derna AND flood AND Libya"`).
- Enforce a minimum 15-second sleep between consecutive GDELT API calls to avoid
  HTTP 429 rate limits. The probe script (test_gdelt.py) uses 12s; the pipeline
  uses 15s.
- GDELT response parsing: check for `text/html` content-type before JSON parsing —
  the API returns HTML error text (not JSON) for some error conditions with HTTP 200.

## Semantic search (multilingual)
- The `news-articles` index uses a `semantic_text` field (`semantic_field`) backed by
  Elastic's in-cluster **`.multilingual-e5-small-elasticsearch`** inference endpoint
  (384-dim dense, multilingual). `title` and `body` `copy_to` this field; Elastic
  embeds them automatically on index.
- **Store articles in their ORIGINAL language.** Do NOT translate before indexing.
  multilingual-e5 embeds all languages into one shared space, so an English query
  retrieves Arabic / French / Greek documents directly. The old Gemini
  `translate_to_english()` step was removed — it was slower, cost Vertex AI calls,
  and lost nuance.
- Hackathon compliance: multilingual-e5 is a **built-in Elastic feature** (partner
  track permitted). Do NOT switch the embedding endpoint to `.openai-*` — that would
  introduce a non-permitted AI provider and disqualify the entry.
- Known limitation: the `-small` model aligns English↔French (same script) more
  tightly than English↔Arabic; Arabic docs are retrievable but rank lower for
  English queries. Upgrade to `-base`/`-large` or retrieve more candidates if needed.
- **Gotcha:** `index_test_data.py` only creates the index `if not exists`. If the
  GDELT pipeline's `es.index()` auto-creates `news-articles` first, it is born with
  plain dynamic text fields and NO semantic field. Always create the index with the
  explicit mapping (run `index_test_data.py`) before the pipeline writes to a fresh
  cluster, or semantic search silently degrades to BM25.

## What the agent does and does not do
- DOES: surface what each source claimed; flag where sources diverge; cite every claim
- DOES NOT: verify truth, score source reliability, produce ground-truth estimates
- Every claim in output must link to its source article — no floating numbers
- Output format is always the four-section structure:
  AGREED FACTS / DIVERGENCE / SOURCE BREAKDOWN / CONFIDENCE SUMMARY

## Repo layout (current)
- src/agent.py — CLI entry point for local testing
- src/app.py — Flask web server; Cloud Run entry point
- scripts/gdelt_pipeline.py — GDELT → Elastic ingestion pipeline
- scripts/index_test_data.py — indexes synthetic fallback articles into Elastic
- scripts/test_gdelt.py — GDELT coverage probe (run before changing demo event)
- scripts/agent_test.py — smoke test: MCP + Gemini connectivity
- scripts/test_mcp.py — smoke test: MCP tools list only
- docs/CHANGELOG.md — append an entry after every meaningful session
- docs/CONVENTIONS.md — this file; update if conventions change
- docs/PROJECT_KNOWLEDGE.md — product context and decisions; update if direction changes
- docs/DEPLOYMENT.md — step-by-step deploy guide for teammates
