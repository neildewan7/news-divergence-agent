import os
import asyncio
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

MCP_ENDPOINT = os.getenv("MCP_ENDPOINT")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY")

async def main():
    client = MultiServerMCPClient({
        "agent-builder": {
            "transport": "streamable_http",
            "url": MCP_ENDPOINT,
            "headers": {"Authorization": f"ApiKey {ELASTICSEARCH_API_KEY}"},
        }
    })
    tools = await client.get_tools()
    print(f"Found {len(tools)} tools:")
    for t in tools:
        print(f"  - {t.name}")

if __name__ == "__main__":
    asyncio.run(main())