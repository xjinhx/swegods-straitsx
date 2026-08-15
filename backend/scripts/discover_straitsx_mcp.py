"""
Direct MCP client — connects to StraitsX's card gateway and lists its tools.
Bypasses Claude Desktop's connector UI entirely (PRD Section 9.2).

Setup:  pip install mcp
Usage:  python discover_straitsx_mcp.py sandbox      # or: production

Run this once to get the real tool name(s) and input schema for card issuance, then
wire app/straitsx_client.py's `_real_issue_card` to call whatever this reveals and
flip MOCK_STRAITSX=false.
"""
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.sse import sse_client

SANDBOX_URL = "https://card.straitsx.ai/sandbox/sse"
PRODUCTION_URL = "https://card.straitsx.ai/production/sse"


async def discover(url: str):
    print(f"Connecting to: {url}\n")
    async with sse_client(url) as (read, write):
        async with ClientSession(read, write) as session:
            init_result = await session.initialize()
            print("=== Server info ===")
            print(f"Name:    {init_result.serverInfo.name}")
            print(f"Version: {init_result.serverInfo.version}\n")

            tools_result = await session.list_tools()
            print(f"=== Available tools ({len(tools_result.tools)}) ===\n")
            for tool in tools_result.tools:
                print(f"--- {tool.name} ---")
                print(f"Description: {tool.description}")
                print("Input schema:")
                print(json.dumps(tool.inputSchema, indent=2))
                print()


def main():
    profile = sys.argv[1] if len(sys.argv) > 1 else "sandbox"
    url = SANDBOX_URL if profile == "sandbox" else PRODUCTION_URL
    try:
        asyncio.run(discover(url))
    except Exception as e:
        print(f"\n!!! Connection failed: {e}")


if __name__ == "__main__":
    main()
