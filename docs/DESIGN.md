# Design — Agentic CRM

A multi-agent system that **acts** on a CRM: it qualifies leads, deflects support
tickets, and runs a research→outreach chain — autonomously, with a human
supervising rather than driving. Built on the 2026 agentic stack (Google ADK +
MCP + A2A) with a glass-box trust layer.

> Business-intelligence / demo only. Synthetic data, no real customer records.

---

## 1. Why this, and the framing

Through 2024 the story was "AI assists" (draft this email, summarize this record).
By 2025–2026 it became "AI acts": qualify the lead, write the outreach, resolve the
ticket — with a human as supervisor/approver. The competitive edge has moved from
smarter single models to the **coordination + governance layer**. This project
demonstrates exactly that layer.

| | Copilot / Assistant | Agent (what this builds) |
|---|---|---|
| Trigger | Human prompts each step | Goal-driven, self-initiated |
| Logic | Single-shot generation | Reason → act → observe → reflect loop |
| Scope | One task | End-to-end multi-step workflow |
| Human role | Operator | Supervisor / approver |

---

## 2. Scope — three connected workflows

Rather than spread thin across many use cases, the MVP goes deep on one connected
story — **qualify → deflect → (research → outreach)** — chosen because together they
exercise every core agentic concept while staying buildable.

| # | Workflow | Pattern | Success metric |
|---|----------|---------|----------------|
| 1 | **Inbound lead qualification & routing** | single agent + CRM tools, confidence handoff | qualified-lead rate |
| 2 | **Support case deflection** | RAG-grounded agent + escalation gate | deflection rate, grounding % |
| 3 | **Meeting-prep → outreach chain** | sequential chain + A2A handoff + approve-before-send | prep time, draft acceptance |

**Deliberately cut** (signals judgment): stale-opp re-engagement, churn, data hygiene,
marketing, coaching; auth/multi-tenancy/billing; a full React dashboard; A2A on every
seam (only one seam is A2A); multiple live LLM providers.

---

## 3. Agentic concepts → where they live in this CRM

| Concept | In this system |
|---------|----------------|
| Goal / task | a CRM workflow outcome ("resolve this ticket", "qualify this lead") |
| Planning / decomposition | the Orchestrator classifies the event and sequences the flow |
| Perception / grounding | reads CRM records (MCP) + KB chunks (RAG) |
| Reasoning | Qualifier scoring, deflection answer selection |
| Tool use | CRM read/write exposed as **MCP** tools |
| Short-term memory | per-run ADK session state |
| Long-term memory | persistent lead/account state in the CRM + run log in SQLite |
| Grounding / RAG | deflection answers anchored to retrieved KB chunks, with citations |
| Action / actuation | writes back to the CRM (lead score, ticket reply, tasks) |
| Reflection / self-correction | each agent scores confidence vs. the goal; low → escalate |
| Handoff | Qualifier→rep, Deflection→human, Researcher→Outreach (**A2A**) |
| Guardrails / HITL | confidence thresholds, approve-before-send, kill-switch |
| Observability | per-step glass-box trace (plan→act→reflect, confidence, cost) |
| Interoperability | **MCP** for tools, **A2A** for agent-to-agent |

---

## 4. Architecture

```
inbound event  (new lead | new ticket | "prep me for meeting with X")
        │
   ┌────▼─────────────────────────────────────────┐
   │  Orchestrator / Router (ADK supervisor)        │
   │  classify event → set goal/budget → dispatch    │
   └──┬──────────────┬───────────────────┬─────────┘
      ▼              ▼                    ▼
 ┌─────────┐   ┌──────────────┐   ┌──────────────────────┐
 │Qualifier│   │ Deflection    │   │ Researcher           │
 │ score + │   │ RAG over KB + │   │ account/activity     │
 │ route   │   │ account ctx,  │   │ → meeting brief      │
 │ (MCP)   │   │ escalate <conf│   │        │             │
 └────┬────┘   └──────┬────────┘   │        ▼ (A2A)        │
      ▼               ▼            │ ┌──────────────────┐  │
  🧑 route OK?    🧑 human         │ │ Outreach Writer  │  │ ← A2A peer
                  (low-conf)       │ │ (peer service)   │  │   (Agent Card)
                                   │ └────────┬─────────┘  │
                                   │   🧑 approve-before-send
                                   └──────────────────────┘
        CRM updated  +  glass-box trace (confidence · cost · escalations · kill-switch)
```

**Layers every agent shares:** context (CRM + KB), memory (session + persistent),
tools (MCP catalog), guardrails (confidence/approval/kill-switch), reflection
(confidence scoring), observability (trace).

---

## 5. Tech stack & rationale

| Layer | Choice | Why |
|-------|--------|-----|
| Orchestration | **Google ADK** | explicit orchestration primitives + native MCP & A2A; lighter than LangGraph |
| LLM | **Groq** (Llama 3.1 8B / 3.3 70B) via ADK `LiteLlm` | fast tier for triage/retrieval, strong tier for reasoning/outreach; provider-agnostic (Anthropic/Gemini swap via model string + key) |
| Tools | **MCP** server (14 CRM tools) via `MCPToolset` | the standard "agent → tools" interface; one governed action catalog |
| Agent-to-agent | **A2A** (`to_a2a()`/`RemoteA2aAgent`) on one seam | demonstrates "MCP for tools, A2A for agents" without full distributed overhead |
| CRM store | **SQLite** (default) or **Airtable**, behind `CRMStore` | offline+reproducible for evals; Airtable for demo "feel"; one-line swap |
| RAG | **Chroma** + local MiniLM embeddings | grounding without an API key for retrieval |
| API | **FastAPI** | agent runtime + HITL endpoints |

See [`DECISIONS.md`](DECISIONS.md) for the trade-offs behind each choice.

---

## 6. Milestone roadmap

| | Milestone | Status |
|---|-----------|--------|
| M0 | Scaffold, CRM stores, synthetic seed, MCP server (14 tools) | ✅ done |
| M1 | RAG core — `/ingest` + `/ask`, citations | ✅ done (retrieval 5/5 top-1) |
| M2 | Deflection agent + eval harness (deflection rate, grounding %) | ⬜ |
| M3 | Qualifier agent (score + route, writes back to CRM) | ⬜ |
| M4 | Orchestrator/router (classify → dispatch) | ⬜ |
| M5 | Researcher→Outreach A2A chain + HITL approve-before-send | ⬜ |
| M6 | Glass-box trace + governance (kill-switch, eval numbers) | ⬜ |
| M7 | Stretch — React control tower, more A2A seams, re-engagement | ⬜ |

---

## 7. Evaluation plan

Run on fixed fixtures (`backend/eval/fixtures/`):

- **Deflection rate** — % tickets resolved without escalation (target a believable 50–70%)
- **Grounding rate** — % of deflection claims with a valid retrieved source (target 100%)
- **Citation correctness** — does the cited KB chunk actually support the answer?
- **Qualification accuracy** — agent route vs. labeled "should-route-to"
- **Escalation precision** — of escalated cases, how many truly needed a human
- **Cost / latency per run** — reported per run

---

## 8. Repository layout

```
backend/
  app.py            FastAPI surface (/health, /ingest, /ask, + later /event, /approve, /trace, /kill)
  config.py         env config + CRMStore factory
  llm.py            LiteLlm → Claude (fast/smart tiers)
  crm/              CRMStore interface + SQLite & Airtable backends + synthetic seed
  mcp/crm_server.py MCP server — 14 CRM tools
  agents/           ADK agents (orchestrator, qualifier, deflection, researcher, outreach) + MCP toolset
  a2a/              Outreach Writer as an A2A peer service
  rag/              ingest (chunk+embed→Chroma) + retrieve (top-k + grounded answer)
  eval/             fixtures + run_eval.py
docs/               this design, decisions log, archived prior design
```
