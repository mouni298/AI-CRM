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

## ADR-003 — Groq via ADK's LiteLlm wrapper (provider-agnostic)
**Decision:** Run Groq-hosted Llama models (3.1 8B for triage/retrieval, 3.3 70B for
reasoning/outreach) through ADK's `LiteLlm` wrapper rather than ADK's native Gemini
path. The wrapper keeps the provider behind a model-string + env-key, so Anthropic
or Gemini is a one-line swap.
**Why:** Groq has a generous free tier and very low latency (LPU inference), which
suits an agentic loop making many calls — good for a buildable, runnable portfolio
demo without per-token cost. Tiering fast vs. strong per agent still applies.
**Trade-off:** Open-weight Llama models are less capable than frontier Claude/Gemini
on hard reasoning; if deflection/qualification quality lags, bump MODEL_SMART to a
larger Groq model or switch the provider (the LiteLlm indirection makes this free).

## ADR-002 — Google ADK for orchestration (over LangGraph)
**Decision:** Use Google ADK as the agent framework.
**Why:** Native A2A support (`to_a2a()`, `RemoteA2aAgent`) and native MCP
(`MCPToolset`) — the two protocols this project showcases — plus first-class
orchestration primitives (`LlmAgent` + `sub_agents`, `SequentialAgent`). LangGraph
would have meant tracing *its* internals rather than a clean plan→act→reflect log we
own, and a heavier abstraction.
**Trade-off:** Another framework's conventions; observability is OpenTelemetry-shaped.
ADK's A2A is the decisive factor (ADR-006).
