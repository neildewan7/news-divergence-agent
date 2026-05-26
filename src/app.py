import os
import time
import asyncio
import threading
import warnings
warnings.filterwarnings("ignore", message="Key '.*' is not supported in schema")

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv()

DEBUG = False

SYSTEM_PROMPT = (
    "You are a news analysis assistant. When asked about an event, "
    "use the platform_core_search tool to find articles in the 'news-articles' "
    "index in Elasticsearch. After finding articles, report what each source said. "
    "Pay special attention to differences in casualty counts, attribution, "
    "and framing between sources. Cite each claim to its source."
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

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True, silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400

    async def _run():
        return await _agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    t_start = time.time()
    result = asyncio.run_coroutine_threadsafe(_run(), _loop).result(timeout=120)
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
        "execution_time_seconds": elapsed,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
