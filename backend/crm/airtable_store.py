"""Airtable-backed CRMStore — the demo "feel" backend.

Lets you watch records change in a real grid during a Loom walkthrough. Not the
default: the SQLite backend is what evals/CI use. Activate with CRM_BACKEND=airtable.

Expected base layout — one table per entity, named exactly:
    Accounts, Contacts, Leads, Deals, Tickets, Activities, Tasks, KBArticles
Each table has a text field `id` holding our domain id (e.g. "acc-001"); other
fields match the dataclass attributes in base.py. Seed with:
    CRM_BACKEND=airtable python -m backend.crm.seed_airtable   (see that script)
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from .base import (
    Account,
    Activity,
    Contact,
    CRMStore,
    Deal,
    KBArticle,
    Lead,
    Task,
    Ticket,
)

_API = "https://api.airtable.com/v0"


class AirtableStore(CRMStore):
    def __init__(self, api_key: str, base_id: str) -> None:
        if not api_key or not base_id:
            raise ValueError(
                "AirtableStore needs AIRTABLE_API_KEY and AIRTABLE_BASE_ID "
                "(set CRM_BACKEND=sqlite to run fully offline instead)."
            )
        self.base_id = base_id
        self.client = httpx.Client(
            base_url=f"{_API}/{base_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    # --- low-level helpers ---------------------------------------------------
    def _list(self, table: str, formula: Optional[str] = None) -> list[dict]:
        params: dict[str, Any] = {}
        if formula:
            params["filterByFormula"] = formula
        records, offset = [], None
        while True:
            if offset:
                params["offset"] = offset
            r = self.client.get(f"/{table}", params=params)
            r.raise_for_status()
            data = r.json()
            records.extend(data.get("records", []))
            offset = data.get("offset")
            if not offset:
                break
        return records

    def _find_one(self, table: str, domain_id: str) -> Optional[dict]:
        recs = self._list(table, f"{{id}} = '{domain_id}'")
        return recs[0] if recs else None

    def _patch(self, table: str, rec_id: str, fields: dict[str, Any]) -> dict:
        r = self.client.patch(f"/{table}/{rec_id}", json={"fields": fields})
        r.raise_for_status()
        return r.json()["fields"]

    def _create(self, table: str, fields: dict[str, Any]) -> dict:
        r = self.client.post(f"/{table}", json={"fields": fields})
        r.raise_for_status()
        return r.json()["fields"]

    # --- accounts / contacts -------------------------------------------------
    def get_account(self, account_id: str) -> Optional[Account]:
        rec = self._find_one("Accounts", account_id)
        return Account(**rec["fields"]) if rec else None

    def find_account(self, name: str) -> Optional[Account]:
        recs = self._list("Accounts", f"FIND(LOWER('{name}'), LOWER({{name}}))")
        return Account(**recs[0]["fields"]) if recs else None

    def list_contacts(self, account_id: str) -> list[Contact]:
        recs = self._list("Contacts", f"{{account_id}} = '{account_id}'")
        return [Contact(**r["fields"]) for r in recs]

    # --- leads ---------------------------------------------------------------
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        rec = self._find_one("Leads", lead_id)
        return Lead(**rec["fields"]) if rec else None

    def list_leads(self, status: Optional[str] = None) -> list[Lead]:
        formula = f"{{status}} = '{status}'" if status else None
        return [Lead(**r["fields"]) for r in self._list("Leads", formula)]

    def update_lead(self, lead_id: str, **fields: Any) -> Lead:
        rec = self._find_one("Leads", lead_id)
        if not rec:
            raise KeyError(f"lead {lead_id} not found")
        merged = {**rec["fields"], **self._patch("Leads", rec["id"], fields)}
        return Lead(**merged)

    # --- deals / activities --------------------------------------------------
    def list_deals(
        self, account_id: Optional[str] = None, stage: Optional[str] = None
    ) -> list[Deal]:
        parts = []
        if account_id:
            parts.append(f"{{account_id}} = '{account_id}'")
        if stage:
            parts.append(f"{{stage}} = '{stage}'")
        formula = f"AND({','.join(parts)})" if parts else None
        return [Deal(**r["fields"]) for r in self._list("Deals", formula)]

    def list_activities(self, account_id: str, limit: int = 20) -> list[Activity]:
        recs = self._list("Activities", f"{{account_id}} = '{account_id}'")
        acts = [Activity(**r["fields"]) for r in recs]
        acts.sort(key=lambda a: a.days_ago)
        return acts[:limit]

    # --- tickets -------------------------------------------------------------
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        rec = self._find_one("Tickets", ticket_id)
        return Ticket(**rec["fields"]) if rec else None

    def list_tickets(self, status: Optional[str] = None) -> list[Ticket]:
        formula = f"{{status}} = '{status}'" if status else None
        return [Ticket(**r["fields"]) for r in self._list("Tickets", formula)]

    def update_ticket(self, ticket_id: str, **fields: Any) -> Ticket:
        rec = self._find_one("Tickets", ticket_id)
        if not rec:
            raise KeyError(f"ticket {ticket_id} not found")
        merged = {**rec["fields"], **self._patch("Tickets", rec["id"], fields)}
        return Ticket(**merged)

    # --- tasks ---------------------------------------------------------------
    def create_task(
        self, account_id: str, contact_id: str, kind: str, title: str, body: str
    ) -> Task:
        n = len(self._list("Tasks")) + 1
        task_id = f"task-{n:03d}"
        fields = dict(
            id=task_id, account_id=account_id, contact_id=contact_id,
            kind=kind, title=title, body=body, status="pending",
        )
        self._create("Tasks", fields)
        return Task(**fields)

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        formula = f"{{status}} = '{status}'" if status else None
        return [Task(**r["fields"]) for r in self._list("Tasks", formula)]

    def update_task(self, task_id: str, **fields: Any) -> Task:
        rec = self._find_one("Tasks", task_id)
        if not rec:
            raise KeyError(f"task {task_id} not found")
        merged = {**rec["fields"], **self._patch("Tasks", rec["id"], fields)}
        return Task(**merged)

    # --- knowledge base ------------------------------------------------------
    def list_kb_articles(self) -> list[KBArticle]:
        out = []
        for r in self._list("KBArticles"):
            f = dict(r["fields"])
            tags = f.get("tags", [])
            if isinstance(tags, str):  # tolerate JSON-string or comma list
                try:
                    tags = json.loads(tags)
                except json.JSONDecodeError:
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
            out.append(KBArticle(id=f["id"], title=f["title"], body=f["body"], tags=tags))
        return out
