import os
import time
import asyncio
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

    # Initialize Gemini via Vertex AI
    llm = ChatVertexAI(
        model="gemini-2.5-flash",
        project="news-divergence-project",
        location="us-central1",
    )

    # Create a ReAct agent that can decide when to call tools
    agent = create_react_agent(
        llm,
        tools=tools,
        prompt=(
            "You are a news analysis assistant. When asked about an event, "
            "use the platform_core_search tool to find articles in the 'noto-earthquake-articles' "
            "index in Elasticsearch. After finding articles, you MUST write a response that: "
            "1) Lists what each source reported including the source name and date "
            "2) Compares death toll numbers across sources "
            "3) Notes differences in framing between Japanese and English sources "
            "4) Highlights any concepts that appear in Japanese sources but not English ones "
            "Always produce a written response. Never return empty output."
        ),
    )

    # Test query
    query = (
    "What happened in the 2024 Noto Peninsula earthquake in Japan? "
    "Search the noto-earthquake-articles index and tell me what each source reported, "
    "highlighting any differences between sources — especially differences in death toll numbers, "
    "the concept of disaster-related deaths, and how Japanese vs English sources framed the event."
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
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
