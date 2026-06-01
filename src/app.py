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
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from gdelt_pipeline import populate_index_for_query

load_dotenv()

DEBUG = False

SYSTEM_PROMPT = (
    "You are a humanitarian news analysis assistant helping researchers understand "
    "how the same disaster or conflict event is reported across different sources.\n\n"
    "When given a query, use the platform_core_search tool to search the news-articles "
    "Elasticsearch index. IMPORTANT: always include time_range when calling "
    "platform_core_search — set from to 'now-3y' and to to 'now' unless the user "
    "specifies a different period. Never call the tool without time_range.\n\n"
    "Structure your response in exactly these FIVE sections, using the exact headers shown:\n\n"
    "## AGREED FACTS\n"
    "Bullet points of claims confirmed by multiple sources.\n\n"
    "## DIVERGENCE\n"
    "For each factual disagreement, list exactly which source reported what. "
    "Always flag casualty count conflicts explicitly.\n\n"
    "## SOURCE BREAKDOWN\n"
    "One line per source, pipe-delimited, exactly this format:\n"
    "- NAME | TYPE | LANG | DATE | One sentence on their framing angle\n"
    "TYPE must be one of: wire, ngo, government, local_press, international, unknown\n"
    "LANG must be ISO 639-1 code (en, ar, fr, da, ps, el, es, etc.)\n"
    "DATE must be the article publish date as YYYY-MM-DD, or 'unknown'\n"
    "Example: - Reuters | wire | en | 2023-09-13 | Focused on official death toll of 3800.\n\n"
    "## CLAIM MATRIX\n"
    "One line per disputed claim, pipe-delimited, exactly this format:\n"
    "CLAIM | SOURCE:VALUE:STATUS | SOURCE:VALUE:STATUS | ...\n"
    "STATUS must be 'agree' (corroborated by another source) or 'conflict' (contradicts another source).\n"
    "Use — for sources that did not report on this claim.\n"
    "Example: Death toll | Reuters:3800:conflict | UN OCHA:11000:conflict | Government:3800:agree\n\n"
    "## CONFIDENCE SUMMARY\n"
    "For each major claim, one line:\n"
    "HIGH confidence (N/N sources agree): [claim]\n"
    "CONTESTED (N sources say X, N sources say Y): [claim]\n\n"
    "Rules: every claim must be cited to its source. Never assert anything beyond what a source "
    "explicitly said. If fewer than 3 sources are found, say so and suggest a broader query."
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
    )
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


# Build the agent in the persistent loop at startup
_agent = asyncio.run_coroutine_threadsafe(_build_agent(), _loop).result(timeout=60)

# Separate lightweight LLM instance for synchronous extraction calls
_extract_llm = ChatVertexAI(
    model="gemini-2.5-flash",
    project="news-divergence-project",
    location="us-central1",
)

app = Flask(__name__)


def extract_query_params(user_query: str) -> dict:
    """
    Ask Gemini to extract GDELT search parameters from a natural-language query.
    Returns {"keywords": str, "start_date": str, "end_date": str} in YYYYMMDD000000 format.
    Falls back to the past 180 days if extraction fails.
    """
    today = datetime.utcnow()
    fallback = {
        "keywords": user_query,
        "start_date": (today - timedelta(days=180)).strftime("%Y%m%d") + "000000",
        "end_date": today.strftime("%Y%m%d") + "000000",
    }

    prompt = (
        "Extract search parameters from this news query. Return JSON only with keys: "
        "keywords (AND-separated terms, no quotes), "
        "start_date (YYYYMMDD000000), end_date (YYYYMMDD000000). "
        "If no date is mentioned, set end_date to today and start_date to 180 days ago. "
        f"Query: {user_query}"
    )

    try:
        response = _extract_llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        # Extract the first JSON object from the response
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            return {
                "keywords": parsed.get("keywords", user_query),
                "start_date": parsed.get("start_date", fallback["start_date"]),
                "end_date": parsed.get("end_date", fallback["end_date"]),
            }
    except Exception as exc:
        print(f"extract_query_params failed: {exc}")

    return fallback


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    # Extract GDELT search parameters from the user query
    params = extract_query_params(query)
    keywords = params["keywords"]
    start_date = params["start_date"]
    end_date = params["end_date"]

    # Index fresh articles from GDELT before running the agent
    try:
        newly_indexed = populate_index_for_query(
            keywords,
            start_date=start_date,
            end_date=end_date,
        )
    except Exception as exc:
        print(f"GDELT pipeline error (non-fatal): {exc}")
        newly_indexed = 0

    async def _run():
        return await _agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    t_start = time.time()
    result = asyncio.run_coroutine_threadsafe(_run(), _loop).result(timeout=180)
    elapsed = round(time.time() - t_start, 2)

    content = result["messages"][-1].content
    if isinstance(content, list):
        response_text = "".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    else:
        response_text = content

    return jsonify({
        "response": response_text,
        "sources_indexed": newly_indexed,
        "execution_time_seconds": elapsed,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
