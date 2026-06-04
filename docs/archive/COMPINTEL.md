# CompIntel — AI Competitive-Research Desk

**A multi-agent + RAG system that researches competitors/markets and produces a sourced report.**
Positioned as *"an AI research analyst for product teams"* — the verifiable, fact-based slice of a PM's research workflow.

> **Status:** Design / pre-build. Portfolio project to showcase agentic orchestration + RAG depth.
> **Legal note:** Business intelligence only — *not* financial/legal/medical advice. Safe to build & share in India as a portfolio/personal demo. See `/memory/legal-sebi-constraint.md`. Avoid securities buy/sell recommendations.

---

## 1. What it does (in one line)

You give it competitors (or a market question) + a document corpus. A team of AI agents splits up the research, retrieves real evidence, debates strengths vs. weaknesses, and hands back a **cited competitive report** in minutes — work that takes a human ~2 days.

This is a portfolio-scale version of products people pay $20K–40K/yr for (Crayon, Klue, Kompyte).

---

## 2. Use cases

| # | Persona | Example query | Output |
|---|---------|---------------|--------|
| 1 | Founder | "Analyze the AI note-taking market — players, gaps, room for a new entrant?" | Market-entry brief + white-space section |
| 2 | Product Manager | "Compare us to Linear and Jira — features, pricing, where each wins" | Side-by-side battle card |
| 3 | Sales / AE | "Brief me on Acme Corp before my call — business, news, pain points" | 1-page account brief + talking points |
| 4 | Marketer | "How do the top 5 CRMs position themselves — what messaging is unclaimed?" | Positioning map + messaging-gap report |
| 5 | Job seeker | "Research Stripe for my interview — model, competitors, challenges" | Company dossier |
| 6 | Analyst (research, not advice) | "Map the cybersecurity industry — segments, leaders, growth drivers" | Industry landscape report |

**Anchor demo (build first):** *"Compare Product A vs Product B — features, pricing, customer sentiment, and who wins for which user."*

---

## 3. Where RAG fits (and where it doesn't)

RAG = retrieve relevant text from a corpus and ground the answer in it. Used here in **three roles** (this is what makes it non-decorative):

1. **Retrieval for facts** — analysts pull specific claims from long docs (pricing pages, filings, whitepapers).
2. **Retrieval for sentiment mining** — sentiment analyst retrieves representative complaints/praise from a large review corpus.
3. **Retrieval for verification (guardrail)** — before shipping, the compliance agent re-queries the store to confirm every claim has a real supporting chunk. Unsupported claims get flagged/removed.

### What goes in RAG vs. live tools

| Data | RAG? | Why |
|------|------|-----|
| User's private docs (customer interviews, support tickets, sales/win-loss notes, battlecards) | ✅✅ best fit | private, large, can't be fetched by tools |
| Scraped review corpora, long PDFs/filings, product docs | ✅ | big, static, reused, citable |
| Tool's own past reports | ✅ (memory) | "what did we conclude last month?" |
| Today's news / announcements | ❌ → web search | fresh, small |
| Live pricing / metrics | ❌ → API tool | real-time |

**Principle:** RAG holds the bulky knowledge you collected and want to search + cite repeatedly. Live facts come from tools. The system combines both.

---

## 4. Architecture

```
User: "Compare Notion vs Coda vs Obsidian"  + [uploaded docs]
        │
   ┌────▼─────────────────────────────────────┐
   │  Orchestrator (Lead)                       │
   │  - ingest corpus → index                   │
   │  - decompose task, set token/cost budget   │
   │  - spawn one analyst per competitor        │
   └────┬───────────────┬───────────────┬──────┘
        ▼               ▼               ▼
  ┌───────────┐  ┌───────────┐   ┌───────────┐
  │ Analyst:  │  │ Analyst:  │   │ Analyst:  │   each: RAG over that
  │ Notion    │  │ Coda      │   │ Obsidian  │   competitor's docs
  │ (RAG+web) │  │ (RAG+web) │   │ (RAG+web) │   + web search (fresh news)
  └─────┬─────┘  └─────┬─────┘   └─────┬─────┘
        └──────────────┼───────────────┘
                       ▼
        ┌──────────────────────────────┐
        │ Sentiment analyst             │  ← RAG over review corpus
        └──────────────┬───────────────┘
                       ▼
        ┌──────────────────────────────┐
        │ Debate: strengths vs gaps     │  ← adversarial, cited
        └──────────────┬───────────────┘
                       ▼
        ┌──────────────────────────────┐
        │ Synthesizer → comparison matrix│
        └──────────────┬───────────────┘
                       ▼
        ┌──────────────────────────────┐
        │ Compliance: re-query store to  │  ← RAG-as-verification
        │ verify every claim is grounded │
        └──────────────┬───────────────┘
                       ▼
                🧑 Human approval (HITL)
                       ▼
            Cited competitive report
```

### Capability coverage

- **Multi-agent orchestration** — parallel analysts, handoffs, debate, synthesis, supervisor pattern
- **RAG (advanced)** — chunking, hybrid search + rerank, citations, retrieval-as-verification
- **Tool use** — web search for fresh news, optional pricing/news APIs
- **Memory** — prior reports per competitor
- **Guardrails + HITL** — citation check + human approval before "ship"
- **Evals** — grounding %, retrieval precision, tool-selection correctness
- **Glass-box trace** — live view of each agent, retrievals, debate, cost
- **Provider-agnostic** — cheap model for retrieval, strong model for synthesis

---

## 5. Tech stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language / backend | **Python + FastAPI** | agent runtime + streaming endpoints |
| Orchestration | **LangGraph** (recommended) or OpenAI Agents SDK | graph = clean topology + traceable; SDK = native handoffs |
| LLM access | **Provider-agnostic** via LiteLLM (or thin wrapper) | swap Anthropic / OpenAI per agent |
| Vector DB | **Chroma** (local, zero-setup) → Qdrant for "production" look | stores chunks + metadata |
| Embeddings | local `sentence-transformers` / BGE (free) or OpenAI `text-embedding-3-small` | |
| Reranker | local cross-encoder (`bge-reranker`) or Cohere free tier | the +15–30% quality win |
| Chunking / loaders | LangChain splitters/loaders or plain Python | section-aware chunking |
| Web search tool | Tavily / Brave API (free tiers) | fresh news only |
| Storage (runs, memory, HITL state) | SQLite (→ Postgres later) | serialized run state for resume |
| Frontend (optional) | React | glass-box trace UI; backend-first is fine for MVP |
| Observability | own trace + optional Langfuse (self-host, free) | |

**Free-tier path:** Chroma + local embeddings + local reranker + Tavily free + one LLM key. ~$0 to run a demo.

---

## 6. MVP scope (build this first)

**Goal:** the smallest slice that produces the full end-to-end trace.

### MVP includes
1. **Ingestion pipeline** — load docs → chunk (+metadata) → embed → store in Chroma
2. **Retrieval pipeline** — embed query → similarity search (top-k) → rerank → return chunks + sources
3. **2 competitor analyst agents** (RAG over corpus + 1 web-search tool)
4. **Debate agent** (strengths vs. weaknesses)
5. **Synthesizer agent** (comparison table + recommendation)
6. **Citation-check guardrail** (re-query store to verify claims)
7. **HITL gate** — approve / request-changes / reject (state serialized)
8. **CLI or minimal API** output (React UI is post-MVP)

### MVP excludes (cut deliberately — note in README)
- Auth, multi-tenancy, billing
- More than 2 competitors / extra analyst types (sentiment, risk) — add after
- Polished UI, scheduled monitoring, Slack integration
- GraphRAG (stretch)

### Milestones
- **M1 — RAG core:** `POST /ingest`, `POST /ask` → sourced answer with citations. *(Proves retrieval works.)*
- **M2 — Single analyst agent:** one agent that RAGs + web-searches one competitor → structured findings.
- **M3 — Orchestration:** orchestrator fans out to 2 analysts in parallel → handoffs.
- **M4 — Debate + synthesis:** combine findings → comparison report.
- **M5 — Guardrail + HITL:** citation verification + human approval gate.
- **M6 — Evals + trace:** grounding %, retrieval precision; glass-box trace output.
- **M7 (stretch):** React trace UI, sentiment/risk analysts, memory.

---

## 7. Worked example (end-to-end)

**Query:** *"Compare Notion vs Coda — features, pricing, what customers complain about, who wins for which user."*
**Corpus provided:** Notion + Coda pricing PDFs, product docs, ~400 scraped reviews each.

**1. Orchestrator** ingests + indexes corpus, plans, spawns 2 analysts + sentiment analyst, sets budget ($0.40 / 120k tokens).

**2. Notion analyst** (parallel):
```json
{ "agent": "analyst:notion",
  "findings": [
    {"claim":"Notion's Business tier is $15/user/mo","source":"notion_pricing.pdf p.2","confidence":0.95},
    {"claim":"Strong all-in-one docs+DB flexibility","source":"product_docs#blocks","confidence":0.9}
  ] }
```

**3. Coda analyst** (parallel): similar structured, cited findings.

**4. Sentiment analyst** (RAG over reviews):
```json
{ "agent":"sentiment",
  "findings":[
    {"claim":"Notion users complain about slowness on large workspaces","source":"review_182","confidence":0.85},
    {"claim":"Coda praised for formulas but called hard to learn","source":"review_91","confidence":0.8}
  ] }
```

**5. Debate:**
> 🟢 *Notion wins on ecosystem + ease for general teams [cites notion findings].*
> 🔴 *Coda wins for data-heavy power users; Notion lags on tables at scale [cites review_182].*

**6. Synthesizer** → comparison table + verdict:
```json
{ "verdict":"Notion for general teams; Coda for data-power users",
  "confidence":0.78,
  "comparison":{"pricing":"...","features":"...","sentiment":"..."},
  "claims":[ /* each linked to a source id */ ] }
```

**7. Compliance guardrail** re-queries store: 9/10 claims grounded; 1 unsupported claim ("Coda is cheaper at scale") → flagged → sent back → removed/fixed.

**8. HITL gate:**
```
REVIEW REQUIRED — Notion vs Coda
Verdict: Notion (general) / Coda (data-power)   Confidence: 78%
Cost: $0.29 / 88k tokens   Grounding: 10/10 cited ✓
[ ✅ Approve ]  [ ✏️ Request changes ]  [ ❌ Reject ]
```
- **Approve** → report finalized, logged to memory.
- **Request changes** ("dig deeper on enterprise pricing") → control returns to orchestrator, re-runs only the relevant analyst, then re-debates/synthesizes (resumable state).
- **Reject** → archived with reason (feeds evals).

---

## 8. Evaluation plan (the credibility numbers)

Run on a fixed set of ~10 questions with known answers:
- **Grounding rate** — % of report claims with a valid retrieved source (target: 100%)
- **Retrieval precision@k** — are the retrieved chunks actually relevant?
- **Citation correctness** — does the cited source actually support the claim?
- **Tool-selection accuracy** — did agents use RAG vs. web search appropriately?
- **Cost / latency per run** — report it ("$0.29, 42s")

Put these numbers in the README — recruiters engage far more with real metrics.

---

## 9. README / presentation checklist (for the portfolio)

- [ ] Problem statement + who it's for
- [ ] Architecture diagram (section 4)
- [ ] **What I chose NOT to build, and why** (signals judgment)
- [ ] RAG design: chunking strategy, hybrid search, rerank, the 3 RAG roles
- [ ] Eval numbers (section 8)
- [ ] 90-second Loom walkthrough + 1 screenshot of the glass-box trace
- [ ] Note on the RAG-vs-long-context-vs-memory tradeoff (shows awareness)
- [ ] "Not investment advice / demo only" disclaimer

---

## 10. Open decisions

- **Framework:** LangGraph vs OpenAI Agents SDK vs from-scratch (recommend LangGraph for visible topology + trace).
- **Demo corpus:** your own sample docs, or generate realistic synthetic reviews/docs?
- **UI:** backend/CLI-first for MVP, React trace UI as stretch — confirm.
- **Review data:** if scraping real review sites, check each site's terms of service first.
