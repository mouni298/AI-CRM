"""FastAPI app — the agentic-CRM control surface.

M0 ships the skeleton + health/CRM-inspection endpoints. Later milestones fill in:
  M1  POST /ingest, POST /ask          (RAG core)
  M2+ POST /event                      (route an inbound lead/ticket to an agent)
  M5  POST /approve                    (HITL approve/request-changes/reject)
  M6  GET  /trace/{run_id}, POST /kill  (glass-box trace + kill-switch)
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config
from .crm.base import to_dict
from .rag import ingest as rag_ingest
from .rag import retrieve as rag_retrieve

app = FastAPI(title="Agentic CRM", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "crm_backend": config.CRM_BACKEND}


# --- M1: RAG core ----------------------------------------------------------
class AskRequest(BaseModel):
    query: str
    k: int = 4


@app.post("/ingest")
def ingest() -> dict:
    """Load the KB from the CRM into Chroma (chunk + embed). Idempotent."""
    n = rag_ingest.ingest_kb(config.get_store())
    return {"ingested_chunks": n, "collection": config.KB_COLLECTION}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    """Grounded, cited answer over the KB."""
    return rag_retrieve.answer(req.query, req.k)


# --- M2: agent flows -------------------------------------------------------
class EventRequest(BaseModel):
    kind: str  # currently: "ticket" (deflection). leads/meetings added in M3/M5.
    id: str


@app.post("/event")
async def event(req: EventRequest) -> dict:
    """Route an inbound CRM event to the right agent flow.

    M2 handles tickets (deflection); the full classify-and-dispatch orchestrator
    arrives in M4. Until then this is an explicit per-kind switch."""
    if req.kind == "ticket":
        from .agents.deflection import deflect

        return await deflect(req.id)
    raise HTTPException(status_code=400, detail=f"unsupported event kind: {req.kind!r}")


@app.get("/crm/leads")
def crm_leads(status: str | None = None) -> list[dict]:
    """Inspect leads (sanity/demo helper)."""
    return to_dict(config.get_store().list_leads(status))


@app.get("/crm/tickets")
def crm_tickets(status: str | None = None) -> list[dict]:
    """Inspect tickets (sanity/demo helper)."""
    return to_dict(config.get_store().list_tickets(status))


# --- placeholders wired in later milestones --------------------------------
# @app.post("/ingest")   -> backend.rag.ingest      (M1)
# @app.post("/ask")      -> backend.rag.retrieve     (M1)
# @app.post("/event")    -> backend.agents.orchestrator (M2-M4)
# @app.post("/approve")  -> HITL gate                (M5)
# @app.get("/trace/{run_id}") / @app.post("/kill")   (M6)
