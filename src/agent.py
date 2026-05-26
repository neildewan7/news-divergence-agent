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
    "You are a news analysis assistant. When asked about an event, "
    "use the platform_core_search tool to find articles in the 'news-articles' "
    "index in Elasticsearch. After finding articles, report what each source said. "
    "Pay special attention to differences in casualty counts, attribution, "
    "and framing between sources. Cite each claim to its source."
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
