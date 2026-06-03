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
    "When given a query, use the platform_core_search tool to find articles.\n\n"
    "CRITICAL — tool call requirements (the tool rejects calls that omit either):\n"
    '  1. index: "news-articles-v2"  (always search this index — it has multilingual '
    "semantic search; do NOT use 'news-articles')\n"
    '  2. time_range: {"from": "now-3y", "to": "now"}\n'
    "Always pass both. Example call: platform_core_search("
    'query="Derna flood casualties", index="news-articles-v2", '
    'time_range={"from":"now-3y","to":"now"}).\n\n'

    "RETRIEVAL — gather BROADLY before analysing:\n"
    "- Your goal is to compare MANY sources, so retrieve as many relevant articles "
    "as you can. Aim for at least 8-10 distinct sources when they exist.\n"
    "- Make MULTIPLE search calls with different angle keywords to widen coverage "
    "(e.g. one for the event + 'casualties', one for + 'death toll', one for "
    "+ 'damage', one for + 'investigation'). Combine all results.\n"
    "- NEVER base the analysis on a single article when more are available. If your "
    "first search returns only one or two sources, run additional searches with "
    "broader or alternative keywords before writing your answer.\n\n"

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
