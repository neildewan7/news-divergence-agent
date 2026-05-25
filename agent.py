import os
import asyncio
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

load_dotenv()

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
            "use the platform_core_search tool to find articles in the 'news-articles' "
            "index in Elasticsearch. After finding articles, report what each source said. "
            "Pay special attention to differences in casualty counts, attribution, "
            "and framing between sources. Cite each claim to its source."
        ),
    )

    # Test query
    query = (
        "What happened in the Kabul market explosion in September 2024? "
        "Search the news-articles index and tell me what each source reported, "
        "highlighting any differences between sources."
    )

    result = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})

    # Print the final response
    print("\n" + "=" * 80)
    print("AGENT RESPONSE:")
    print("=" * 80)
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())