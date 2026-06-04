# Decisions log

Short records of the architectural choices and their trade-offs. Newest first.

---

## ADR-006 — One A2A seam, not all-A2A
**Decision:** Only the Researcher→Outreach handoff goes over A2A; the orchestrator
and other specialists coordinate in-process within ADK.
**Why:** The brief flags "using MCP where A2A is the right abstraction" as a common
error, so demonstrating a *genuine* A2A peer (own task lifecycle, Agent Card
discovery) is worth it. But running all four agents as independent networked
services adds auth/ops cost an MVP doesn't need. One real seam proves understanding
of "MCP for tools, A2A for agents" at a fraction of the cost.
**Trade-off:** Not a fully distributed agent mesh — noted as a deliberate cut.

## ADR-005 — MCP for the CRM tool layer
**Decision:** Expose all CRM read/write as an MCP server; agents consume it via ADK
`MCPToolset`.
**Why:** Matches the 2026 standard ("MCP = the hands"), gives one governed action
catalog that every trace line maps to, and decouples agents from the storage
backend. Bonus: the MCP server is reusable by any MCP client (e.g. Claude Desktop).
**Trade-off:** A stdio subprocess hop per agent session vs. direct function calls —
negligible at this scale, and the governance/portability win dominates.

## ADR-004 — CRM store: SQLite default, Airtable optional, behind one interface
**Decision:** `CRMStore` interface with a SQLite backend (default) and an Airtable
backend, swappable via `CRM_BACKEND`.
**Why:** SQLite is offline, reproducible, and zero-dependency — exactly what the eval
harness and CI need. Airtable gives a real grid you can watch records change in
during a demo ("feel"). Putting both behind one interface means the agents never
care which is active.
**Trade-off:** Two backends to maintain; mitigated by the tight interface surface.

## ADR-003 — Anthropic Claude via ADK's LiteLlm wrapper
**Decision:** Run Claude (Haiku for triage/retrieval, Sonnet for reasoning/outreach)
through ADK's `LiteLlm` model wrapper rather than ADK's native Gemini path.
**Why:** Provider-agnostic, lets us tier cheap vs. strong models per agent, and keeps
the door open to Gemini as a one-line fallback if ADK+Claude tool-calling ever
gives trouble.
**Trade-off:** ADK leans Google-ecosystem (defaults to Gemini, Cloud Trace), so Claude
goes through an extra adapter; acceptable for the model quality + flexibility.

## ADR-002 — Google ADK for orchestration (over LangGraph)
**Decision:** Use Google ADK as the agent framework.
**Why:** Native A2A support (`to_a2a()`, `RemoteA2aAgent`) and native MCP
(`MCPToolset`) — the two protocols this project showcases — plus first-class
orchestration primitives (`LlmAgent` + `sub_agents`, `SequentialAgent`). LangGraph
would have meant tracing *its* internals rather than a clean plan→act→reflect log we
own, and a heavier abstraction.
**Trade-off:** Another framework's conventions; observability is OpenTelemetry-shaped.
ADK's A2A is the decisive factor (ADR-006).

## ADR-001 — Pivot from CompIntel to Agentic CRM
**Decision:** Repurpose this repo from "CompIntel" (a competitive-research desk) to a
multi-agent agentic-CRM system. Prior design archived to `docs/archive/COMPINTEL.md`.
**Why:** CRM is the richest structured customer dataset most companies own, so it's
the most natural home for autonomous agents — and the strongest 2026 portfolio
narrative (orchestration + governance, not just an LLM call). Reuses CompIntel's
RAG, citation-verification, and glass-box-trace ideas.
**Trade-off:** Loses the competitive-research framing; the agentic patterns transfer.
