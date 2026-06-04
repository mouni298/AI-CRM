"""Factory for the CRM MCP toolset that ADK agents attach to.

Spawns backend/mcp/crm_server.py as a stdio subprocess and exposes its tools to
an ADK agent. Every agent that needs to read/write the CRM gets its tools from
here, so the MCP layer is the single, governed action catalog.
"""

from __future__ import annotations

import sys
from pathlib import Path

from google.adk.tools.mcp_tool import MCPToolset, StdioConnectionParams
from mcp import StdioServerParameters

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def crm_toolset() -> MCPToolset:
    """An MCPToolset backed by our stdio CRM server (uses the current venv python)."""
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=["-m", "backend.mcp.crm_server"],
                cwd=str(_PROJECT_ROOT),
            ),
            timeout=30,
        )
    )
