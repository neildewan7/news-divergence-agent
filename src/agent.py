import os
import time
import asyncio
import warnings
warnings.filterwarnings("ignore", message="Key '.*' is not supported in schema")

from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import AIMessage, ToolMessage

load_dotenv()

DEBUG = True

def debug_print(label, content, truncate=500):
    if not DEBUG:
        return
    text = str(content)
    if len(text) > truncate:
        text = text[:truncate] + "... [truncated]"
    print(f"[DEBUG] {label}: {text}")

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
    "- NAME | TYPE | LANG | DATE | URL | One sentence on their framing angle\n"
    "TYPE must be one of: wire, ngo, government, local_press, international, unknown\n"
    "LANG must be ISO 639-1 code (en, ar, fr, da, ps, el, es, etc.)\n"
    "DATE must be the article publish date as YYYY-MM-DD, or 'unknown'\n"
    "URL must be the full article URL from the search results, or 'unknown'\n"
    "Example: - Reuters | wire | en | 2023-09-13 | https://reuters.com/article/xyz | Focused on official death toll of 3800.\n\n"
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
    "If fewer than 3 sources are found that are relevant to the query, do not attempt an analysis. Instead respond with exactly:INSUFFICIENT SOURCES: Only N relevant articles found for this query. Try a more specific date range or different keywords."
    )

async def main():
    # Connect to Elastic MCP
    client = MultiServerMCPClient({
        "agent-builder": {
            "transport": "streamable_http",
            "url": os.getenv("MCP_ENDPOINT"),
            "headers": {"Authorization": f"ApiKey {os.getenv('ELASTICSEARCH_API_KEY')}"},
        }
    })
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools")

    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project="news-divergence-project",
        location="us-central1",
    )

    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

    # Test query
    query = (
        "What happened in the Kabul market explosion in September 2024? "
        "Search the news-articles index and tell me what each source reported, "
        "highlighting any differences between sources."
    )

    t_start = time.time()
    result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
    elapsed = time.time() - t_start

    

    # Debug: walk every message in the agent's internal trace
    if DEBUG:
        for i, msg in enumerate(result["messages"]):
            print(f"\n===== STEP {i} =====")
            if isinstance(msg, AIMessage):
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"TOOL CALL: {tc['name']}")
                        debug_print("args", tc["args"])
                else:
                    debug_print("GEMINI", msg.content)
            elif isinstance(msg, ToolMessage):
                print(f"TOOL RESPONSE [{msg.name}]:")
                debug_print("content", msg.content)

    print(f"\nExecution time: {elapsed:.2f}s")

    # Print the final response
    print("\n" + "=" * 80)
    print("AGENT RESPONSE:")
    print("=" * 80)
    content = result["messages"][-1].content
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    print(content)

if __name__ == "__main__":
    asyncio.run(main())
