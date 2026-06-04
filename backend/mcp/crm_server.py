"""MCP server exposing the CRM as a tool catalog — the agents' "hands".

This is the brief's "MCP = the standard interface between an AI brain and its
hands" made concrete. ADK agents consume these tools via MCPToolset (stdio).
Every tool is a thin wrapper over the configured CRMStore, returning plain
JSON-serializable dicts so results render cleanly in the glass-box trace.

Run standalone (stdio):  python -m backend.mcp.crm_server
"""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

from ..config import get_store
from ..crm.base import to_dict

mcp = FastMCP("crm")
store = get_store()


# --- accounts / contacts ---------------------------------------------------
@mcp.tool()
def get_account(account_id: str) -> dict:
    """Fetch a single account (company) by id."""
    return to_dict(store.get_account(account_id)) or {"error": "not_found"}


@mcp.tool()
def find_account(name: str) -> dict:
    """Find an account by (partial) company name. Used for 'prep me for <company>'."""
    return to_dict(store.find_account(name)) or {"error": "not_found"}


@mcp.tool()
def list_contacts(account_id: str) -> list[dict]:
    """List the contacts (people) at an account."""
    return to_dict(store.list_contacts(account_id))


# --- leads (qualifier flow) ------------------------------------------------
@mcp.tool()
def get_lead(lead_id: str) -> dict:
    """Fetch an inbound lead by id."""
    return to_dict(store.get_lead(lead_id)) or {"error": "not_found"}


@mcp.tool()
def list_leads(status: Optional[str] = None) -> list[dict]:
    """List leads, optionally filtered by status (new/qualified/disqualified/handoff)."""
    return to_dict(store.list_leads(status))


@mcp.tool()
def update_lead(
    lead_id: str,
    status: Optional[str] = None,
    score: Optional[float] = None,
    routed_to: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Write qualification results back to a lead: status, fit score, routing, notes."""
    fields = {
        k: v
        for k, v in dict(status=status, score=score, routed_to=routed_to, notes=notes).items()
        if v is not None
    }
    return to_dict(store.update_lead(lead_id, **fields))


# --- deals / activities (researcher flow) ----------------------------------
@mcp.tool()
def list_deals(account_id: Optional[str] = None, stage: Optional[str] = None) -> list[dict]:
    """List deals, optionally filtered by account and/or pipeline stage."""
    return to_dict(store.list_deals(account_id, stage))


@mcp.tool()
def list_activities(account_id: str, limit: int = 20) -> list[dict]:
    """List recent activities (calls/emails/meetings/notes) for an account, newest first."""
    return to_dict(store.list_activities(account_id, limit))


# --- tickets (deflection flow) ---------------------------------------------
@mcp.tool()
def get_ticket(ticket_id: str) -> dict:
    """Fetch a support ticket by id."""
    return to_dict(store.get_ticket(ticket_id)) or {"error": "not_found"}


@mcp.tool()
def list_tickets(status: Optional[str] = None) -> list[dict]:
    """List support tickets, optionally filtered by status (open/resolved/escalated)."""
    return to_dict(store.list_tickets(status))


@mcp.tool()
def update_ticket(
    ticket_id: str,
    reply: Optional[str] = None,
    status: Optional[str] = None,
    resolved_by: Optional[str] = None,
) -> dict:
    """Write a resolution to a ticket: reply text, status, and who resolved it."""
    fields = {
        k: v
        for k, v in dict(reply=reply, status=status, resolved_by=resolved_by).items()
        if v is not None
    }
    return to_dict(store.update_ticket(ticket_id, **fields))


# --- tasks (handoffs + outreach drafts) ------------------------------------
@mcp.tool()
def create_task(account_id: str, contact_id: str, kind: str, title: str, body: str) -> dict:
    """Create a follow-up task: a rep handoff, a meeting-prep brief, or an outreach draft."""
    return to_dict(store.create_task(account_id, contact_id, kind, title, body))


@mcp.tool()
def list_tasks(status: Optional[str] = None) -> list[dict]:
    """List tasks, optionally filtered by status (pending/approved/sent/rejected)."""
    return to_dict(store.list_tasks(status))


@mcp.tool()
def update_task(task_id: str, status: Optional[str] = None, body: Optional[str] = None) -> dict:
    """Update a task — e.g. approve/reject an outreach draft or revise its body."""
    fields = {k: v for k, v in dict(status=status, body=body).items() if v is not None}
    return to_dict(store.update_task(task_id, **fields))


if __name__ == "__main__":
    mcp.run(transport="stdio")
