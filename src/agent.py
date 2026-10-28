"""Run LinkPlus as a local terminal agent backed by its MCP server."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
MCP_SERVER = PROJECT_ROOT / "src" / "mcp_server.py"


async def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_openai_api_key_here":
        print("Error: set OPENAI_API_KEY in .env before starting LinkPlus.")
        return

    server_params = {
        "command": sys.executable,
        "args": [str(MCP_SERVER)],
        "cwd": str(PROJECT_ROOT),
        "env": dict(os.environ),
    }
    async with MCPServerStdio(
        params=server_params,
        name="LinkPlus-MCP",
        client_session_timeout_seconds=30,
    ) as mcp_server:
        agent = Agent(
            name="LinkPlus Assistant",
            instructions=(
                "You are LinkPlus, a professional-network assistant. Use local CSV tools for "
                "searches and network statistics. Only call get_profile_details or "
                "compare_connections when the user explicitly requests enrichment or comparison. "
                "Only set allow_web_search to true when the user explicitly requests public-web "
                "search snippets. Clearly identify each result's source and never present missing "
                "fields as facts. For comparisons, use a concise Markdown table followed by notes."
            ),
            mcp_servers=[mcp_server],
        )

        print("\n=========================================")
        print("LinkPlus AI Agent is ready! (Type 'exit' to quit)")
        print("=========================================")

        while True:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ("exit", "quit"):
                return
            if not user_input:
                continue
            try:
                result = await Runner.run(agent, input=user_input)
            except Exception as error:  # Keep the interactive shell alive after a failed run.
                print(f"\nLinkPlus error: {error}")
                continue
            print(f"\nLinkPlus:\n{result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
