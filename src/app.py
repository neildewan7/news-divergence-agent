import os
import sys
import re
import json
import time
import asyncio
import threading
import warnings
warnings.filterwarnings("ignore", message="Key '.*' is not supported in schema")

from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from elasticsearch import Elasticsearch
import requests as _requests
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from gdelt_pipeline import populate_index_for_query, search_gdelt, index_articles

load_dotenv()

DEBUG = False

SYSTEM_PROMPT = (
    "You are a humanitarian news analysis assistant helping researchers understand "
    "how the same disaster or conflict event is reported across different sources.\n\n"
    "When given a query, use the platform_core_search tool to search the news-articles "
    "Elasticsearch index.\n\n"
    "CRITICAL: you MUST always pass time_range when calling platform_core_search. "
    "The tool will reject calls that omit it. Always use exactly this structure:\n"
    '  time_range: {"from": "now-3y", "to": "now"}\n'
    "Never call platform_core_search without time_range — it will fail with a validation error.\n\n"

    "SOURCE NAMING RULES:\n"
    "- Every source name must come from the search result metadata (the 'source' or domain field).\n"
    "- If no display name is available, use the domain exactly as it appears (e.g. 'aa.com.tr').\n"
    "- Never invent, guess, or paraphrase a source name. Never write 'Unknown Source'.\n"
    "- If multiple articles share the same domain, same date, and near-identical figures, "
    "treat them as ONE source (a wire story reprinted). Note this in SOURCE BREAKDOWN as "
    "'[Domain] (via [wire agency] — reprinted by N outlets)'.\n\n"

    "Structure your response in exactly these FOUR sections, using the exact headers shown:\n\n"

    "## AGREED FACTS\n"
    "Bullet points of claims confirmed by two or more independent sources "
    "(wire reprintings count as one source). Cite each claim: (source1, source2).\n\n"

    "## DIVERGENCE\n"
    "Only flag a divergence when two or more NAMED sources give materially different "
    "information: numbers that differ by more than 5%, or directly contradictory factual "
    "assertions. Do NOT flag: the same figure rounded differently, one source providing "
    "more detail than another, or opinion differences.\n\n"
    "For each material divergence, use this format:\n"
    "**[CLAIM TOPIC]**\n"
    "- [Source Name] ([date]): [exactly what they said]\n"
    "- [Source Name] ([date]): [exactly what they said]\n"
    "Significance: [one sentence on why this matters for humanitarian analysis]\n\n"

    "## SOURCE BREAKDOWN\n"
    "One line per source, pipe-delimited, exactly this format:\n"
    "- NAME | TYPE | LANG | DATE | URL | One sentence on their framing angle\n"
    "TYPE must be one of: wire, ngo, government, local_press, international, opinion, unknown\n"
    "LANG must be ISO 639-1 code (en, ar, fr, el, es, etc.)\n"
    "DATE must be the article publish date as YYYY-MM-DD, or 'unknown'\n"
    "URL must be the full article URL from the search results, or 'unknown'\n"
    "Example: - aa.com.tr | wire | en | 2023-09-13 | https://aa.com.tr/en/article/xyz | Reported official death toll of 3845.\n\n"

    "## CONFIDENCE SUMMARY\n"
    "For each major claim, one line:\n"
    "HIGH confidence (N/N sources agree): [claim]\n"
    "CONTESTED (N sources say X, N sources say Y): [claim]\n\n"

    "Hard rules:\n"
    "- Every claim must be cited to its source. Never assert anything beyond what a source explicitly said.\n"
    "- If fewer than 3 independent sources are found, say so clearly and suggest a broader query.\n"
    "- opinion-type sources may be listed in SOURCE BREAKDOWN but should not anchor claims in AGREED FACTS.\n"
    "- If fewer than 2 material divergences exist, write 'No material divergences identified' "
    "in the DIVERGENCE section rather than inventing minor differences."
)

# One persistent event loop in a background thread so gRPC channels (Vertex AI)
# are never called from a different or closed loop.
_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, daemon=True).start()


async def _build_agent():
    client = MultiServerMCPClient({
        "agent-builder": {
            "transport": "streamable_http",
            "url": os.getenv("MCP_ENDPOINT"),
            "headers": {"Authorization": f"ApiKey {os.getenv('ELASTICSEARCH_API_KEY')}"},
        }
    })
    tools = await client.get_tools()
    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project="news-divergence-project",
        location="us-central1",
        temperature=0.1,
    )
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


# Build the agent in the persistent loop at startup
_agent = asyncio.run_coroutine_threadsafe(_build_agent(), _loop).result(timeout=60)

# Separate lightweight LLM instance for synchronous extraction calls
_extract_llm = ChatVertexAI(
    model="gemini-2.5-flash",
    project="news-divergence-project",
    location="us-central1",
    temperature=0.1,
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _es_client() -> Elasticsearch:
    return Elasticsearch(
        os.getenv("ELASTICSEARCH_ENDPOINT"),
        api_key=os.getenv("ELASTICSEARCH_API_KEY"),
    )


def _es_count(index: str = "news-articles") -> int:
    try:
        return _es_client().count(index=index)["count"]
    except Exception as exc:
        print(f"ES count error: {exc}")
        return -1


def _es_relevant_count(keywords: str, index: str = "news-articles") -> int:
    """Return how many docs match all query terms (AND logic) in body or title."""
    # Strip GDELT AND operators so "Derna AND flood" → "Derna flood"
    clean = " ".join(w for w in keywords.split() if w.upper() != "AND").strip()
    try:
        resp = _es_client().count(
            index=index,
            body={
                "query": {
                    "multi_match": {
                        "query": clean,
                        "fields": ["title", "body"],
                        "operator": "and",
                    }
                }
            },
        )
        return resp["count"]
    except Exception as exc:
        print(f"ES relevant count error: {exc}")
        return 0


def _es_sample(index: str = "news-articles", size: int = 5) -> list:
    try:
        resp = _es_client().search(
            index=index,
            body={
                "query": {"match_all": {}},
                "_source": ["title", "source", "source_type", "published_date", "language"],
                "size": size,
                "sort": [{"published_date": {"order": "desc", "unmapped_type": "date"}}],
            },
        )
        return [h["_source"] for h in resp["hits"]["hits"]]
    except Exception as exc:
        return [{"error": str(exc)}]


def _gdelt_status() -> str:
    """Returns 'ok' or 'rate_limited' by making a single minimal GDELT probe request."""
    try:
        r = _requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": "Derna AND Libya",
                "startdatetime": "20230910000000",
                "enddatetime": "20230911000000",
                "maxrecords": 1,
                "mode": "artlist",
                "format": "json",
            },
            headers={"User-Agent": "news-divergence-agent/1.0"},
            timeout=10,
        )
        return "rate_limited" if r.status_code == 429 else "ok"
    except Exception as exc:
        return f"error: {exc}"


def extract_query_params(user_query: str) -> dict:
    """
    Ask Gemini to extract GDELT search parameters from a natural-language query.
    Returns {"keywords": str, "start_date": str, "end_date": str} in YYYYMMDD000000 format.
    Falls back to the past 180 days if extraction fails.
    """
    today = datetime.utcnow()
    today_str = today.strftime("%Y%m%d") + "000000"
    fallback = {
        "keywords": user_query,
        "start_date": (today - timedelta(days=180)).strftime("%Y%m%d") + "000000",
        "end_date": today_str,
    }

    prompt = (
        "Extract search parameters from this news query. "
        "Return a JSON object with exactly these keys:\n"
        "  keywords: AND-separated search terms (no quotes, no dates)\n"
        f"  start_date: format YYYYMMDD000000 (today is {today_str[:8]})\n"
        "  end_date: format YYYYMMDD000000\n"
        "If no date range is mentioned, set end_date to today and start_date to 180 days ago.\n"
        "Return ONLY the JSON object, no markdown, no explanation.\n"
        f"Query: {user_query}"
    )

    try:
        response = _extract_llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        # Find the outermost JSON object (handles nested braces)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(text[start:end])
            keywords = str(parsed.get("keywords", user_query)).strip()
            start_date = str(parsed.get("start_date", fallback["start_date"])).strip()
            end_date = str(parsed.get("end_date", fallback["end_date"])).strip()
            # Sanity-check: dates must be 14-char numeric strings
            if (keywords and
                    re.fullmatch(r"\d{14}", start_date) and
                    re.fullmatch(r"\d{14}", end_date)):
                return {"keywords": keywords, "start_date": start_date, "end_date": end_date}
    except Exception as exc:
        print(f"extract_query_params failed: {exc}")

    return fallback


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/debug")
def debug():
    return jsonify({
        "index": {
            "total_docs": _es_count(),
            "sample_docs": _es_sample(),
        },
        "gdelt_status": _gdelt_status(),
        "system_prompt": SYSTEM_PROMPT,
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "").strip()
    want_debug = request.args.get("debug", "").lower() == "true"

    if not query:
        return jsonify({"error": "query is required"}), 400

    params = extract_query_params(query)
    keywords = params["keywords"]
    start_date = params["start_date"]
    end_date = params["end_date"]

    if want_debug:
        docs_before = _es_count()

        try:
            gdelt_df = search_gdelt(keywords, start_date, end_date)
            gdelt_found = len(gdelt_df)
            # Only probe GDELT for rate limit if we got 0 results — avoids extra
            # request when the pipeline already returned articles.
            if gdelt_found == 0:
                gdelt_rate_limited = (_gdelt_status() == "rate_limited")
            else:
                gdelt_rate_limited = False
            newly_indexed = index_articles(gdelt_df)
        except Exception as exc:
            print(f"GDELT pipeline error (non-fatal): {exc}")
            gdelt_found = 0
            gdelt_rate_limited = True
            newly_indexed = 0

        docs_after = _es_count()

        debug_info = {
            "gdelt_articles_found": gdelt_found,
            "gdelt_articles_indexed": newly_indexed,
            "gdelt_rate_limited": gdelt_rate_limited,
            "articles_in_index_before": docs_before,
            "articles_in_index_after": docs_after,
            "relevant_docs_for_query": _es_relevant_count(keywords),
        }
    else:
        relevant = _es_relevant_count(keywords)
        if relevant >= 10:
            print(f"Found {relevant} relevant docs for query — skipping GDELT pipeline.")
            newly_indexed = 0
        else:
            print(f"Found {relevant} relevant docs — running GDELT pipeline.")
            try:
                newly_indexed = populate_index_for_query(
                    keywords,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as exc:
                print(f"GDELT pipeline error (non-fatal): {exc}")
                newly_indexed = 0
        debug_info = None

    # Build an enriched agent query: strip raw dates from user text and
    # prepend the extracted keywords so the Elastic semantic search vector
    # is focused on event terms rather than date noise.
    clean_keywords = " ".join(w for w in keywords.split() if w.upper() != "AND")
    agent_query = (
        f"Search for articles about: {clean_keywords}\n"
        f"Original user query: {query}\n"
        f"Date range: {start_date[:8]} to {end_date[:8]}\n"
        "Analyse how different sources reported this event."
    )

    async def _run():
        return await _agent.ainvoke({"messages": [{"role": "user", "content": agent_query}]})

    t_start = time.time()
    try:
        result = asyncio.run_coroutine_threadsafe(_run(), _loop).result(timeout=180)
    except Exception as exc:
        elapsed = round(time.time() - t_start, 2)
        print(f"Agent error: {exc}")
        err_resp = {
            "error": "Agent failed to complete — the search tool returned a validation error. Try rephrasing your query.",
            "detail": str(exc),
            "execution_time_seconds": elapsed,
        }
        if want_debug:
            err_resp["debug"] = debug_info
        return jsonify(err_resp), 500
    elapsed = round(time.time() - t_start, 2)

    content = result["messages"][-1].content
    if isinstance(content, list):
        response_text = "".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        response_text = content

    resp = {
        "response": response_text,
        "sources_indexed": newly_indexed,
        "execution_time_seconds": elapsed,
    }
    if want_debug:
        resp["debug"] = debug_info

    return jsonify(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
