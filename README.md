# Agentic CRM — multi-agent system over a CRM

A portfolio project showing **multi-agent orchestration + RAG-grounded automation**
over a CRM, with a glass-box trust layer (traces, confidence, escalation,
kill-switch). Built on the **2026 agentic stack**: Google ADK for orchestration,
**MCP** for tools, **A2A** for agent-to-agent handoff.

> Business-intelligence / demo only. Synthetic data; no real customer records.

## What it does

One orchestrated system covering three connected CRM workflows:

1. **Inbound lead qualification & routing** — scores a lead against ICP data, writes
   the routing decision back to the CRM, hands low-confidence leads to a human.
2. **Support case deflection** — answers tickets grounded in a knowledge base (RAG),
   escalating when confidence is low.
3. **Meeting-prep → outreach chain** — a Researcher agent assembles an account brief,
   then hands off (over **A2A**) to an Outreach Writer, gated by human approval.

## Architecture

```
inbound event ─► Orchestrator/Router (ADK supervisor)
                   ├─ Qualifier  (CRM tools via MCP, confidence handoff)
                   ├─ Deflection (RAG over KB + account ctx, escalation gate)
                   └─ Researcher ─(A2A)─► Outreach Writer ─► human approve-before-send
                              glass-box trace · confidence · cost · kill-switch
```

## Tech stack

| Layer | Choice |
|-------|--------|
| Orchestration | **Google ADK** (`LlmAgent`, `SequentialAgent`) |
| LLM | **Anthropic Claude** via ADK `LiteLlm` (Haiku + Sonnet tiers; Gemini fallback) |
| Tools | **MCP** server (14 CRM tools) consumed via `MCPToolset` |
| Agent-to-agent | **A2A** (`to_a2a()` / `RemoteA2aAgent`) on the Researcher→Outreach seam |
| CRM store | **SQLite** (default, offline) or **Airtable** (demo feel) behind one interface |
| RAG | **Chroma** + local MiniLM embeddings |
| API | **FastAPI** |

## Status

Milestone-based build (see [the plan](#)):

- ✅ **M0** — scaffold, CRM store (SQLite + Airtable), synthetic seed, MCP server (14 tools)
- ✅ **M1** — RAG core: `POST /ingest` + `POST /ask` (retrieval verified 5/5 top-1)
- ⬜ **M2** — deflection agent + eval harness (deflection rate, grounding %)
- ⬜ **M3** — qualifier agent · **M4** — orchestrator/router
- ⬜ **M5** — Researcher→Outreach A2A chain + HITL · **M6** — glass-box trace + governance

## Run it

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY (only needed for /ask + agents)

.venv/bin/python -m backend.crm.seed     # seed data/crm.db
.venv/bin/python -m backend.rag.ingest   # build the KB vector index
.venv/bin/uvicorn backend.app:app --reload
# GET /health · POST /ingest · POST /ask {"query":"how do I reset my password?"}
```

The default SQLite backend runs fully offline; set `CRM_BACKEND=airtable` for the
Airtable demo grid.
