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
  GDELT coverage, richer casualty-count divergence across wire/NGO/government sources, stronger humanitarian framing.
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
- ~~Cloud Run redeployment with updated code~~ — done Day 4
- Frontend (weakest judging criterion)
- Arabic-language articles not yet appearing — GDELT coverage for Arabic may need
  a separate query (e.g. `درنة AND فيضان`) or language filter
- Demo video
- Devpost submission

## 2026-05-31 — Day 4 (Neil)

### Progress
- Cloud Run redeployed with full Day 3 codebase (GDELT pipeline, new SYSTEM_PROMPT,
  `extract_query_params`). Build succeeded in ~2m; service revision
  `news-divergence-agent-00001-9wk` live at
  https://news-divergence-agent-314861703491.us-central1.run.app
- Live smoke test passed: 4-section structured response returned in 19.9s.
  `sources_indexed: 0` — correct, all 40 Libya/Derna articles already in index
  from Day 3 local run (SHA256 dedup working as intended).
- Elastic index audit: 40 docs with `event_id: libya-derna-2023-09`, 0 Kabul
  docs remaining. Mapping uses dynamic text+keyword subfields (not the explicit
  keyword mapping in index_test_data.py) — queries must use `field.keyword`
  for term/agg operations, not bare field name.
- GDELT API rate-limited from local IP during pre-warm attempt; index already
  sufficient for demo with 40 real articles from Day 3.

## 2026-06-01 — Day 5 (Neil)

### Progress
- Expanded `classify_source()` domain lists in `scripts/gdelt_pipeline.py`:
  - wire: added `rfi.fr`, `france24.com`, `africanews.com`, `thepeninsulaqatar.com`
  - international: added `english.aawsat.com`, `globalsecurity.org`
  - local_press: added `skai.gr`, `hurriyetdailynews.com`, `lancashiretelegraph.co.uk`
  - ngo: added `amnesty.org`
  - government: added explicit `_GOVERNMENT` set (`unsmil.unmissions.org`, `un.org`)
    alongside existing `.gov` catch-all
  Previously ~80% of indexed articles from the Libya/Derna GDELT pull were
  classified as "unknown"; after this fix the SOURCE BREAKDOWN section in agent
  responses will show correct type labels for all major sources found.

## 2026-06-01 — Day 5 continued (Clara)

### Progress
- Flask `/` route added to `src/app.py` — serves the frontend via `render_template`.
- `src/templates/` directory created; Flask template lookup confirmed working when
  running `python src/app.py`.
- `src/templates/index.html` (new) — initial frontend attempt: dark theme, header bar, sidebar, metrics strip, two-column layout (source reports + divergence map / SITREP tabs). Visual reference: Figma "Build Divergence Dashboard" export in repo root.
  Status: **work in progress — design not yet satisfactory.**
- Fixed 500 error on `/analyze`: Gemini was calling `platform_core_search` without
  the required `time_range.from` field, triggering MCP error -32602. Fix: added
  explicit instruction to SYSTEM_PROMPT — "always include time_range when calling
  platform_core_search, set from to 'now-3y' and to to 'now'".

### Decisions
- Frontend served directly from Flask (no separate React dev server or build step)
  so it works identically locally and on Cloud Run without config changes.
- Frontend calls `/analyze` via relative URL — no CORS headers needed (same origin).

### Open
- ~~Frontend design needs significant revision~~ — new UI shipped Day 6
- Arabic-language GDELT coverage for Derna
- ~~Cloud Run redeployment~~ — done Day 6
- Demo video
- Devpost submission

## 2026-06-02 — Day 6 (Neil + Clara)

### Decisions
- **Removed divergence map tab**: the CLAIM MATRIX table was unreliable — Gemini
  copied `:VALUE:STATUS` placeholders from the prompt example into the header row,
  making the parser return 0 rows every time. SITREP draft is now the only
  right-panel view.
- **Skip GDELT pipeline when index is warm**: if the index already has ≥ 50 docs,
  bypass all GDELT API calls and go straight to the agent. Eliminates 45–90s of
  dead waiting on repeat queries against the same event.
- **URLs in source cards**: added URL as 6th pipe field in SOURCE BREAKDOWN prompt;
  agent pulls the article URL from Elasticsearch search results and the UI renders
  a clickable "↗ View article" link on each source card.

### Progress
- Clara's new UI merged (dark theme, sidebar, metrics strip, SITREP panel) via
  merge commit; app.py kept (debug endpoint, GDELT pipeline integration).
- `scripts/gdelt_pipeline.py` (Clara): added multilingual GDELT passes (Arabic,
  French, Greek via `sourcelang:` filter), Gemini auto-translation of non-English
  article bodies (`translate_to_english()`), `body_original` field in index docs.
- Concurrent article fetch: replaced sequential `fetch_article_text()` loop with
  `ThreadPoolExecutor(max_workers=10)`. 15 articles now fetch in parallel
  (bounded by single 5s timeout) instead of up to 75s sequentially.
- Capped article fetch at 15 per GDELT pass; reduced trafilatura timeout from 10s
  to 5s using `requests.get()` directly for precise timeout control.
- `GDELT_SLEEP` reduced from 15s to 5s (429s handled by 20s backoff retry).
- SYSTEM_PROMPT synced between `app.py` and `agent.py`: both now use 5-section
  format (AGREED FACTS / DIVERGENCE / SOURCE BREAKDOWN / CLAIM MATRIX /
  CONFIDENCE SUMMARY). `app.py` retains the CRITICAL `time_range` instruction
  that prevents MCP tool validation 500 errors.
- Fixed markdown rendering in SITREP DISPUTED CLAIMS section: added `mdInline()`
  helper that converts `**bold**` → `<strong>` before injecting into innerHTML.
  Previously `esc()` was used which left `**` as literal text.
- DIVERGENT CLAIMS metric now counts bullet points from DIVERGENCE section
  (reliable) instead of parsed CLAIM MATRIX rows (unreliable).
- `scripts/backfill_source_types.py` — one-off script: scrolls all index docs,
  re-runs `classify_source()`, bulk-updates any with stale `source_type: unknown`.
  11/76 docs updated on first run.
- `GET /debug` endpoint: returns index doc count, 5 sample docs, current
  SYSTEM_PROMPT, and a live GDELT rate-limit probe.
- `POST /analyze?debug=true`: adds debug block with GDELT articles found/indexed,
  rate limit status, and index doc count before/after pipeline.

### Performance (end-to-end, warm index ≥50 docs)
- GDELT pipeline: skipped (0s)
- Agent + Elastic MCP search: ~30s
- Total: ~30s vs ~90s before

### Open
- ~~Cloud Run redeployment~~ — done Day 7
- ~~Arabic GDELT coverage~~ — sourcelang:Arabic pass added Day 7
- Demo video
- Devpost submission

## 2026-06-02 — Day 7 (Neil)

### Audit findings (pre-implementation)
- CLAIM MATRIX section in prompt was generating `:VALUE:STATUS` header literals
  and zero usable rows — known broken since Day 6 but never removed from app.py
- `map_language("Greek")` returned `"gr"` (wrong) instead of `"el"` (ISO 639-1)
  via the `[:2].lower()` fallback
- `event_id` hardcoded to `"libya-derna-2023-09"` for ALL articles regardless of
  query — Gaza articles got Libya's event_id
- Future-dated articles contaminating corpus: GDELT `seendate` is the recrawl time,
  not publication time; 2023 articles recrawled in 2026 got `published_date: 2026-*`
- `extract_query_params` regex `{[^{}]+}` failed on markdown-wrapped JSON responses
- ~60% of indexed articles had `source_type: unknown` because classify_source()
  was missing major outlets (aa.com.tr, cnn.com, dw.com, foxnews.com, hrw.org, etc.)
- No materiality threshold for divergence — rounding differences flagged identically
  to 3x casualty count discrepancies
- No wire-story deduplication instruction — 6 outlets reprinting AFP counted as 6 sources

### Group 1: Critical bug fixes
- `temperature=0.1` added to both `ChatVertexAI` instances in `src/app.py` (main
  agent LLM and `_extract_llm`) to reduce non-determinism across runs
- `index_articles()` gains `max_date` and `event_id` parameters; `populate_index_for_query()`
  passes `end_date` as `max_date` — future-recrawled articles rejected at index time
- `event_id` is now derived from query date range instead of hardcoded
- `classify_source()` expanded with 20+ domains: wire (aa.com.tr, xinhuanet.com,
  tass.com, anadoluagency.com), international (cnn.com, dw.com, foxnews.com,
  artnews.com, washingtonpost.com, middleeasteye.net, the-star.co.ke),
  local_press (tolonews.com, pajhwok.com, ariananews.com, protothema.gr),
  ngo (hrw.org, acleddata.com), government (state.gov, fco.gov.uk)
- Added `opinion` source type: mondaq.com, antiwar.com, algemeiner.com, etc.
- Fixed `map_language()`: Greek `"gr"` → `"el"`, added de/es/pt/ru/tr
- Re-ran `backfill_source_types.py`: 23/234 docs updated (wire +3, international +14,
  local_press +6, opinion +4)

### Group 2: Multilingual query expansion
- `populate_index_for_query()` now runs up to 5 GDELT passes:
  1. English primary keywords
  2. English synonym variants (`_synonym_query`: flood→flooding, earthquake→quake, etc.)
  3. French, 4. Arabic, 5. Greek with `sourcelang:` filter
- Added `_synonym_query()`, `_df_language_counts()`, `_df_source_type_counts()` helpers
- Pipeline logs per-pass stats and total found/indexed/by-language/by-source-type

### Group 3: System prompt overhaul
- Reduced to **FOUR sections**: AGREED FACTS / DIVERGENCE / SOURCE BREAKDOWN /
  CONFIDENCE SUMMARY. CLAIM MATRIX removed entirely.
- SOURCE NAMING RULES block added: every name must come from metadata; never invent
  or write "Unknown Source"; use domain if no display name
- Wire-story deduplication instruction: same domain + date + near-identical figures
  = ONE source; note reprinting in SOURCE BREAKDOWN
- DIVERGENCE materiality threshold: only flag when numbers differ >5% or assertions
  directly contradict. "No material divergences identified" is valid.
- DIVERGENCE now uses `**[TOPIC]** / bullet / Significance:` structured format
- `opinion` sources listed in SOURCE BREAKDOWN but excluded from anchoring AGREED FACTS
- Synced `src/agent.py` SYSTEM_PROMPT to match

### Group 4: Self-directed improvements
- `extract_query_params()`: strips markdown code fences, uses `rfind/find` for
  outermost JSON (handles nesting), validates dates with `\d{14}` fullmatch, includes
  today's date in prompt for accurate relative date generation
- Enriched agent query: extracts clean event keywords from GDELT params, passes
  these + original query + date range to agent — reduces date-noise dilution in
  Elastic semantic search vector
- Debug path now includes `relevant_docs_for_query` in response

### Group 5: Validation (two runs, same query)
- Both runs: all 4 sections present, no "Unknown Source", `sources_indexed: 0`,
  10 named real sources per run
- Divergence counts: Run 1 = 2, Run 2 = 3 (diff of 1, within ≤2 threshold)
- Infrastructure damage divergence was present in both but only flagged by Run 2 —
  legitimate marginal case given materiality threshold, not fabrication
- Agent execution time: 44s / 42s (consistent)
- Source type `aa.com.tr` still shows as "international" in agent output — agent
  infers type from knowledge rather than reading `source_type` field from index;
  the indexed field is now correctly set to "wire" after backfill

### Open
- Cloud Run redeployment with Day 7 code
- Agent to read `source_type` from index metadata instead of inferring
- Demo video
- Devpost submission
