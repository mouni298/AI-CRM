"""CRMStore — the abstraction every agent acts on.

Two implementations back this interface:
  - SqliteStore   : offline, reproducible, zero external deps (default).
  - AirtableStore : real grid you can watch records change in (demo "feel").

The agents never import a concrete store; they call the CRM through the MCP
server, which holds one CRMStore instance. Swapping the backend is a one-line
change in config — see backend/config.py.
"""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Domain model
# --------------------------------------------------------------------------- #
# Kept deliberately small but realistic: the entities the three MVP flows touch
# (qualify → deflect → research→outreach). Every record is a flat dataclass so
# it serializes cleanly to JSON for MCP tool results and the glass-box trace.


@dataclass
class Account:
    id: str
    name: str
    industry: str
    size: str           # "smb" | "mid" | "enterprise"
    region: str
    health: str = "ok"  # "ok" | "at_risk" | "churning"


@dataclass
class Contact:
    id: str
    account_id: str
    name: str
    title: str
    email: str


@dataclass
class Lead:
    id: str
    name: str
    email: str
    company: str
    source: str                     # "webform" | "demo_request" | "content" ...
    industry: str = ""
    company_size: str = ""          # "smb" | "mid" | "enterprise"
    budget_band: str = ""           # "none" | "low" | "mid" | "high"
    intent_signals: str = ""        # free text, e.g. "asked about pricing, 3 visits"
    status: str = "new"             # "new" | "qualified" | "disqualified" | "handoff"
    score: Optional[float] = None   # 0..1 ICP-fit confidence written by Qualifier
    routed_to: str = ""             # rep/queue the lead was routed to
    notes: str = ""


@dataclass
class Deal:
    id: str
    account_id: str
    name: str
    stage: str                      # "prospecting".."closed_won"/"closed_lost"
    amount: float
    owner: str
    last_activity_days: int = 0     # days since last touch (drives "stale" later)


@dataclass
class Ticket:
    id: str
    account_id: str
    contact_id: str
    subject: str
    body: str
    priority: str = "normal"        # "low" | "normal" | "high" | "urgent"
    status: str = "open"            # "open" | "resolved" | "escalated"
    reply: str = ""                 # agent/human resolution text
    resolved_by: str = ""           # "agent:deflection" | "human" | ""


@dataclass
class Activity:
    id: str
    account_id: str
    contact_id: str
    kind: str                       # "email" | "call" | "meeting" | "note"
    summary: str
    days_ago: int = 0


@dataclass
class Task:
    """A unit of follow-up work: rep handoffs, and outreach drafts pending send."""
    id: str
    account_id: str
    contact_id: str
    kind: str                       # "handoff" | "outreach_draft" | "meeting_prep"
    title: str
    body: str
    status: str = "pending"         # "pending" | "approved" | "sent" | "rejected"


@dataclass
class KBArticle:
    id: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)


def to_dict(record: Any) -> dict:
    """Serialize a dataclass record (or list of them) for MCP / JSON / trace."""
    if isinstance(record, list):
        return [to_dict(r) for r in record]  # type: ignore[return-value]
    if dataclasses.is_dataclass(record) and not isinstance(record, type):
        return dataclasses.asdict(record)
    return record


# --------------------------------------------------------------------------- #
# Store interface
# --------------------------------------------------------------------------- #


class CRMStore(ABC):
    """The full catalog of CRM reads/writes the agents are allowed to perform.

    These methods map 1:1 to the MCP tools exposed in backend/mcp/crm_server.py.
    Keep the surface tight: each method is an action an agent can take and a line
    that shows up in the glass-box trace.
    """

    # --- accounts / contacts -------------------------------------------------
    @abstractmethod
    def get_account(self, account_id: str) -> Optional[Account]: ...

    @abstractmethod
    def find_account(self, name: str) -> Optional[Account]: ...

    @abstractmethod
    def list_contacts(self, account_id: str) -> list[Contact]: ...

    # --- leads (qualifier flow) ---------------------------------------------
    @abstractmethod
    def get_lead(self, lead_id: str) -> Optional[Lead]: ...

    @abstractmethod
    def list_leads(self, status: Optional[str] = None) -> list[Lead]: ...

    @abstractmethod
    def update_lead(self, lead_id: str, **fields: Any) -> Lead: ...

    # --- deals / activities (researcher flow) -------------------------------
    @abstractmethod
    def list_deals(
        self, account_id: Optional[str] = None, stage: Optional[str] = None
    ) -> list[Deal]: ...

    @abstractmethod
    def list_activities(self, account_id: str, limit: int = 20) -> list[Activity]: ...

    # --- tickets (deflection flow) ------------------------------------------
    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]: ...

    @abstractmethod
    def list_tickets(self, status: Optional[str] = None) -> list[Ticket]: ...

    @abstractmethod
    def update_ticket(self, ticket_id: str, **fields: Any) -> Ticket: ...

    # --- tasks (handoffs + outreach drafts) ---------------------------------
    @abstractmethod
    def create_task(
        self, account_id: str, contact_id: str, kind: str, title: str, body: str
    ) -> Task: ...

    @abstractmethod
    def list_tasks(self, status: Optional[str] = None) -> list[Task]: ...

    @abstractmethod
    def update_task(self, task_id: str, **fields: Any) -> Task: ...

    # --- knowledge base (RAG ingestion source) ------------------------------
    @abstractmethod
    def list_kb_articles(self) -> list[KBArticle]: ...
