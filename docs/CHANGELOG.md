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

## 2026-05-28 — Day 3 (Neil)

### Decisions
- **Demo case pivoted**: Kabul market explosion → Libya/Derna floods, September 2023
  (Storm Daniel, two dam collapses, 10–11 Sep 2023). Rationale: better multilingual
  GDELT coverage, richer casualty-count divergence across wire/NGO/government sources,
  stronger humanitarian framing.
- **GDELT as live corpus source**: queries GDELT Doc 2.0 API at request time and indexes
  fresh articles before each agent run. Replaces hand-curated corpus.
- **Do NOT use gdeltdoc Filters for keyword queries**: the library wraps multi-word
  keywords in double quotes (exact phrase), returning 0–1 results. Direct HTTP requests
  with `AND`-separated keywords return 50 results for the same event.
- **Gemini date extraction**: `/analyze` calls Gemini before GDELT to extract structured
  query params (keywords, start_date, end_date) from the user's natural language query.
  Falls back to past 180 days if no date can be extracted.
- **Structured four-section output** locked in via SYSTEM_PROMPT:
  AGREED FACTS / DIVERGENCE / SOURCE BREAKDOWN / CONFIDENCE SUMMARY.

### Progress
- `scripts/test_gdelt.py` — GDELT coverage probe; confirmed 50 articles available
  for Libya/Derna event with AND keyword syntax across English, French, Greek
- `scripts/gdelt_pipeline.py` — full pipeline:
  - `search_gdelt()`: direct requests, 15s inter-call sleep, auto-widens date ±7d
    on 0 results, rate-limit retry with backoff
  - `fetch_article_text()`: trafilatura, 10s timeout, never raises
  - `classify_source()`: maps domain → wire/international/local_press/ngo/government/unknown
  - `map_language()`: GDELT language name → ISO 639-1 code
  - `index_articles()`: SHA256(url) dedup via mget batch check; bulk index new docs
  - `populate_index_for_query()`: orchestrates the above; prints runtime
- `scripts/index_test_data.py` — updated to Libya/Derna synthetic fallback data
  (5 articles, sources labelled Synthetic*, clearly not real reporting)
- `src/app.py` — updated:
  - New SYSTEM_PROMPT (4-section structured format)
  - `extract_query_params()`: Gemini call → JSON keywords + dates
  - `/analyze` endpoint now calls GDELT pipeline before agent; response includes
    `sources_indexed` count
- `requirements.txt` — added: `gdeltdoc`, `pandas`, `trafilatura`, `elasticsearch`,
  `lxml_html_clean`
- End-to-end test passed locally: 50 GDELT articles found, 30 indexed (20 paywalled),
  agent returned structured 4-section response with ≥2 casualty-count conflicts cited
  to named sources. Total latency ~40s.

### GDELT rate-limit findings
- GDELT Doc 2.0 API enforces ~1 request per 5 seconds globally per IP
- 12s between test-script queries is reliable; pipeline uses 15s
- Exact-phrase queries ("Derna flood Libya") return almost nothing for historical events
- `word1 AND word2 AND word3` syntax returns full 50-article pages reliably

### Open
- Cloud Run redeployment with updated code (GDELT pipeline + new system prompt)
- Frontend (weakest judging criterion)
- Arabic-language articles not yet appearing — GDELT coverage for Arabic may need
  a separate query (e.g. `درنة AND فيضان`) or language filter
- Demo video
- Devpost submission
