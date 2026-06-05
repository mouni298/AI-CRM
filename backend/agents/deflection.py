"""Deflection agent — resolve a support ticket from the KB, or escalate.

The agent loop, in CRM terms:
  perceive  : load the ticket + its account context, retrieve relevant KB chunks
  reason    : draft a grounded answer and self-score confidence
  reflect   : guardrail — escalate if confidence is low, nothing was cited, or the
              model flagged it as needing a human
  act       : write the resolution (or escalation) back to the CRM

Retrieval is done deterministically in code (already verified) and fed to the
agent; the agent decides answer + confidence + escalation. This keeps the run
evaluable while still being a real ADK LlmAgent grounded in RAG.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents import LlmAgent

from .. import config
from ..crm.base import Account, CRMStore, Ticket
from ..llm import smart
from ..rag.retrieve import Chunk, retrieve
from .runner import run_structured
from .schemas import DeflectionDecision

_INSTRUCTION = """You are a support deflection agent for a product-analytics SaaS.
You are given a support ticket, the customer's account context, and KB sources.

Rules:
- Answer ONLY from the provided sources. Never use outside knowledge.
- Cite the KB article id for each claim, e.g. [kb-003], and list ids in cited_articles.
- Set should_escalate=true (and leave answer empty) when the sources do NOT resolve
  the ticket, or when it needs a human: billing/refund disputes, data loss, legal or
  contract terms, suspected bugs, or feature requests.
- confidence is your honest 0..1 estimate that your answer fully resolves the ticket
  from the sources alone. If you're unsure, score low.
Return only the structured fields."""


def build_agent() -> LlmAgent:
    """The deflection LlmAgent (strong model, structured verdict, no tool transfers)."""
    return LlmAgent(
        name="deflection",
        model=smart(),
        instruction=_INSTRUCTION,
        output_schema=DeflectionDecision,
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


def _prompt(ticket: Ticket, account: Optional[Account], chunks: list[Chunk]) -> str:
    acct = (
        f"{account.name} — {account.industry}, {account.size}, {account.region}, "
        f"health={account.health}"
        if account
        else "unknown"
    )
    sources = "\n\n".join(f"[{c.article_id}] {c.title}\n{c.text}" for c in chunks) or "(none)"
    return (
        f"ACCOUNT: {acct}\n\n"
        f"TICKET {ticket.id} (priority={ticket.priority}):\n"
        f"Subject: {ticket.subject}\n{ticket.body}\n\n"
        f"KB SOURCES:\n{sources}"
    )


async def deflect(
    ticket_id: str, store: Optional[CRMStore] = None, k: int = 4
) -> dict:
    """Run the agent on one ticket, apply the escalation guardrail, write back to CRM."""
    store = store or config.get_store()
    threshold = config.CONFIDENCE_THRESHOLD

    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        raise KeyError(f"ticket {ticket_id} not found")
    account = store.get_account(ticket.account_id)
    chunks = retrieve(f"{ticket.subject}. {ticket.body}", k)

    decision = await run_structured(
        build_agent(), _prompt(ticket, account, chunks), DeflectionDecision,
        session_id=ticket_id,
    )

    # Reflection guardrail: the model's self-assessment is necessary but not
    # sufficient — we also enforce a confidence floor and require real citations.
    escalate = (
        decision.should_escalate
        or decision.confidence < threshold
        or not decision.cited_articles
    )

    if escalate:
        store.update_ticket(ticket_id, status="escalated", resolved_by="")
        outcome = "escalated"
    else:
        store.update_ticket(
            ticket_id, status="resolved", resolved_by="agent:deflection",
            reply=decision.answer,
        )
        outcome = "resolved"

    return {
        "ticket_id": ticket_id,
        "outcome": outcome,
        "confidence": decision.confidence,
        "cited_articles": decision.cited_articles,
        "should_escalate": decision.should_escalate,
        "reason": decision.reason,
        "retrieved": [c.article_id for c in chunks],
        "answer": decision.answer if outcome == "resolved" else "",
    }
