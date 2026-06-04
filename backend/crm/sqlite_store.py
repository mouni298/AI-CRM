"""SQLite-backed CRMStore — the default, offline, reproducible backend.

One file on disk (data/crm.db). No external service, no API key, deterministic
across runs once seeded. This is what `eval/run_eval.py` and CI use; the
Airtable backend is purely for demo "feel".
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional

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

# Each table mirrors a dataclass in base.py. `tags` (KB) is stored as JSON text.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY, name TEXT, industry TEXT, size TEXT, region TEXT, health TEXT
);
CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY, account_id TEXT, name TEXT, title TEXT, email TEXT
);
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY, name TEXT, email TEXT, company TEXT, source TEXT,
    industry TEXT, company_size TEXT, budget_band TEXT, intent_signals TEXT,
    status TEXT, score REAL, routed_to TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS deals (
    id TEXT PRIMARY KEY, account_id TEXT, name TEXT, stage TEXT, amount REAL,
    owner TEXT, last_activity_days INTEGER
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY, account_id TEXT, contact_id TEXT, subject TEXT, body TEXT,
    priority TEXT, status TEXT, reply TEXT, resolved_by TEXT
);
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY, account_id TEXT, contact_id TEXT, kind TEXT, summary TEXT,
    days_ago INTEGER
);
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY, account_id TEXT, contact_id TEXT, kind TEXT, title TEXT,
    body TEXT, status TEXT
);
CREATE TABLE IF NOT EXISTS kb_articles (
    id TEXT PRIMARY KEY, title TEXT, body TEXT, tags TEXT
);
"""


class SqliteStore(CRMStore):
    def __init__(self, db_path: str = "data/crm.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # --- generic helpers -----------------------------------------------------
    def _row(self, table: str, _id: str) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(f"SELECT * FROM {table} WHERE id = ?", (_id,))
        return cur.fetchone()

    def _update(self, table: str, _id: str, fields: dict[str, Any]) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(
            f"UPDATE {table} SET {cols} WHERE id = ?", (*fields.values(), _id)
        )
        self.conn.commit()

    # --- accounts / contacts -------------------------------------------------
    def get_account(self, account_id: str) -> Optional[Account]:
        r = self._row("accounts", account_id)
        return Account(**dict(r)) if r else None

    def find_account(self, name: str) -> Optional[Account]:
        cur = self.conn.execute(
            "SELECT * FROM accounts WHERE name LIKE ? LIMIT 1", (f"%{name}%",)
        )
        r = cur.fetchone()
        return Account(**dict(r)) if r else None

    def list_contacts(self, account_id: str) -> list[Contact]:
        cur = self.conn.execute(
            "SELECT * FROM contacts WHERE account_id = ?", (account_id,)
        )
        return [Contact(**dict(r)) for r in cur.fetchall()]

    # --- leads ---------------------------------------------------------------
    def get_lead(self, lead_id: str) -> Optional[Lead]:
        r = self._row("leads", lead_id)
        return Lead(**dict(r)) if r else None

    def list_leads(self, status: Optional[str] = None) -> list[Lead]:
        if status:
            cur = self.conn.execute("SELECT * FROM leads WHERE status = ?", (status,))
        else:
            cur = self.conn.execute("SELECT * FROM leads")
        return [Lead(**dict(r)) for r in cur.fetchall()]

    def update_lead(self, lead_id: str, **fields: Any) -> Lead:
        self._update("leads", lead_id, fields)
        lead = self.get_lead(lead_id)
        if lead is None:
            raise KeyError(f"lead {lead_id} not found")
        return lead

    # --- deals / activities --------------------------------------------------
    def list_deals(
        self, account_id: Optional[str] = None, stage: Optional[str] = None
    ) -> list[Deal]:
        clauses, params = [], []
        if account_id:
            clauses.append("account_id = ?"); params.append(account_id)
        if stage:
            clauses.append("stage = ?"); params.append(stage)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = self.conn.execute(f"SELECT * FROM deals{where}", params)
        return [Deal(**dict(r)) for r in cur.fetchall()]

    def list_activities(self, account_id: str, limit: int = 20) -> list[Activity]:
        cur = self.conn.execute(
            "SELECT * FROM activities WHERE account_id = ? ORDER BY days_ago ASC LIMIT ?",
            (account_id, limit),
        )
        return [Activity(**dict(r)) for r in cur.fetchall()]

    # --- tickets -------------------------------------------------------------
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        r = self._row("tickets", ticket_id)
        return Ticket(**dict(r)) if r else None

    def list_tickets(self, status: Optional[str] = None) -> list[Ticket]:
        if status:
            cur = self.conn.execute("SELECT * FROM tickets WHERE status = ?", (status,))
        else:
            cur = self.conn.execute("SELECT * FROM tickets")
        return [Ticket(**dict(r)) for r in cur.fetchall()]

    def update_ticket(self, ticket_id: str, **fields: Any) -> Ticket:
        self._update("tickets", ticket_id, fields)
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            raise KeyError(f"ticket {ticket_id} not found")
        return ticket

    # --- tasks ---------------------------------------------------------------
    def create_task(
        self, account_id: str, contact_id: str, kind: str, title: str, body: str
    ) -> Task:
        # Deterministic id: <kind>-<n>. Avoids any time/random dependency.
        n = self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] + 1
        task = Task(
            id=f"task-{n:03d}",
            account_id=account_id,
            contact_id=contact_id,
            kind=kind,
            title=title,
            body=body,
        )
        self.conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
            (task.id, account_id, contact_id, kind, title, body, task.status),
        )
        self.conn.commit()
        return task

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        if status:
            cur = self.conn.execute("SELECT * FROM tasks WHERE status = ?", (status,))
        else:
            cur = self.conn.execute("SELECT * FROM tasks")
        return [Task(**dict(r)) for r in cur.fetchall()]

    def update_task(self, task_id: str, **fields: Any) -> Task:
        self._update("tasks", task_id, fields)
        r = self._row("tasks", task_id)
        if r is None:
            raise KeyError(f"task {task_id} not found")
        return Task(**dict(r))

    # --- knowledge base ------------------------------------------------------
    def list_kb_articles(self) -> list[KBArticle]:
        cur = self.conn.execute("SELECT * FROM kb_articles")
        return [
            KBArticle(
                id=r["id"], title=r["title"], body=r["body"], tags=json.loads(r["tags"])
            )
            for r in cur.fetchall()
        ]

    # --- bulk insert (used by seed.py) --------------------------------------
    def _wipe(self) -> None:
        for t in (
            "accounts", "contacts", "leads", "deals", "tickets",
            "activities", "tasks", "kb_articles",
        ):
            self.conn.execute(f"DELETE FROM {t}")
        self.conn.commit()

    def insert_account(self, a: Account) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?)",
            (a.id, a.name, a.industry, a.size, a.region, a.health),
        )

    def insert_contact(self, c: Contact) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO contacts VALUES (?,?,?,?,?)",
            (c.id, c.account_id, c.name, c.title, c.email),
        )

    def insert_lead(self, lead: Lead) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO leads VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                lead.id, lead.name, lead.email, lead.company, lead.source,
                lead.industry, lead.company_size, lead.budget_band,
                lead.intent_signals, lead.status, lead.score, lead.routed_to,
                lead.notes,
            ),
        )

    def insert_deal(self, d: Deal) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO deals VALUES (?,?,?,?,?,?,?)",
            (d.id, d.account_id, d.name, d.stage, d.amount, d.owner, d.last_activity_days),
        )

    def insert_ticket(self, t: Ticket) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO tickets VALUES (?,?,?,?,?,?,?,?,?)",
            (t.id, t.account_id, t.contact_id, t.subject, t.body, t.priority,
             t.status, t.reply, t.resolved_by),
        )

    def insert_activity(self, act: Activity) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO activities VALUES (?,?,?,?,?,?)",
            (act.id, act.account_id, act.contact_id, act.kind, act.summary, act.days_ago),
        )

    def insert_kb_article(self, k: KBArticle) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO kb_articles VALUES (?,?,?,?)",
            (k.id, k.title, k.body, json.dumps(k.tags)),
        )

    def commit(self) -> None:
        self.conn.commit()
