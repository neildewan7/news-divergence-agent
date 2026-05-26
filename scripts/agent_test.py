import os
import asyncio
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_mcp_adapters.client import MultiServerMCPClient

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

    # Initialize Gemini via Vertex AI
    llm = ChatVertexAI(
        model="gemini-2.5-flash",   # or whatever current model name is — check Vertex AI console
        project="news-divergence-project",
        location="us-central1",
    )

    # Quick smoke test: just ask Gemini to list the tool names
    tool_names = [t.name for t in tools]
    response = llm.invoke(f"I have access to these tools: {tool_names}. Which ones look most useful for searching news articles?")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())