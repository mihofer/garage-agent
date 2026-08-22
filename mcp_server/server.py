"""garage-knowledge MCP server.

Thin FastMCP wrapper around mcp_server/knowledge.py (which holds all logic
and is unit-testable without fastmcp installed).

Hermes wiring (~/.hermes/config.yaml):
  mcp_servers:
    garage-knowledge:
      command: "/opt/garage/.venv/bin/python"
      args: ["-m", "mcp_server.server"]
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from . import knowledge

mcp = FastMCP("garage-knowledge")


@mcp.tool()
def list_manuals() -> str:
    """List indexed workshop manuals with chunk counts."""
    return json.dumps(knowledge.list_manuals(), ensure_ascii=False)


@mcp.tool()
def search_manuals(query: str, manual: str = "", max_results: int = 5) -> str:
    """Search all indexed workshop manuals. Hybrid keyword+semantic search.

    Returns JSON passages with manual name and page number for citation.
    Use exact part numbers / torque values in the query when applicable.
    """
    return json.dumps(
        knowledge.search_manuals(query, manual or None, max_results), ensure_ascii=False)


@mcp.tool()
def get_page(manual: str, page: int) -> str:
    """Return full text of one manual page (verify a citation before quoting specs)."""
    return json.dumps(knowledge.get_page(manual, page), ensure_ascii=False)


@mcp.tool()
def search_archive(query: str, max_results: int = 8) -> str:
    """Search the local archive of solved forum threads. Returns title, url,
    author, date and a matched snippet. Follow up with get_thread(url)."""
    return json.dumps(knowledge.search_archive(query, max_results), ensure_ascii=False)


@mcp.tool()
def get_thread(url: str) -> str:
    """Return the full body of one archived forum thread by exact url."""
    return json.dumps(knowledge.get_thread(url), ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
