"""Run the JobAI User Profile MCP server (streamable HTTP).

Run:
    python server.py      # serves http://127.0.0.1:8001/mcp by default
"""

import os

from dotenv import load_dotenv

from profile_mcp.server import mcp

load_dotenv()

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("PROFILE_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("PROFILE_MCP_PORT", "8001")),
        streamable_http_path=os.getenv("PROFILE_MCP_PATH", "/mcp"),
    )
