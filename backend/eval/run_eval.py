"""Deflection eval harness — the credibility numbers for the README.

Re-seeds the CRM, runs the deflection agent over every labeled ticket, and reports:
  - Action accuracy   : agent deflect/escalate vs. the label
  - Deflection rate    : % of tickets resolved without a human
  - Grounding rate     : % of resolved tickets that cited a KB article
  - Citation accuracy  : % of correct deflections that cited the expected article
  - Escalation precision: of escalations, % that were truly escalate-worthy

Run:  python -m backend.eval.run_eval
(Needs GROQ_API_KEY in .env. Runs on the SQLite backend for reproducibility.)
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from ..agents.deflection import deflect
from ..crm.seed import seed

_FIXTURES = Path(__file__).parent / "fixtures" / "tickets.json"


async def _run() -> None:
    labels = json.loads(_FIXTURES.read_text())
    store = seed()  # reset ticket statuses for a clean, reproducible run

    rows = []
    t0 = time.perf_counter()
    for i, case in enumerate(labels):
        res = await deflect(case["ticket_id"], store=store)
        action = "deflect" if res["outcome"] == "resolved" else "escalate"
        rows.append({**case, **res, "action": action})
        # gentle throttle to stay under Groq's free-tier tokens-per-minute cap
        if i < len(labels) - 1:
            await asyncio.sleep(2.0)
    elapsed = time.perf_counter() - t0

    n = len(rows)
    resolved = [r for r in rows if r["action"] == "deflect"]
    escalated = [r for r in rows if r["action"] == "escalate"]
    correct_action = [r for r in rows if r["action"] == r["expected_action"]]
    correct_deflect = [r for r in resolved if r["expected_action"] == "deflect"]
    grounded = [r for r in resolved if r["cited_articles"]]
    cited_right = [
        r for r in correct_deflect if r["expected_article"] in r["cited_articles"]
    ]
    true_escalations = [r for r in escalated if r["expected_action"] == "escalate"]

    def pct(a: int, b: int) -> str:
        return f"{(100 * a / b):.0f}% ({a}/{b})" if b else "n/a"

    print("\n── per-ticket ──────────────────────────────────────────────")
    for r in rows:
        ok = "✓" if r["action"] == r["expected_action"] else "✗"
        cite = ",".join(r["cited_articles"]) or "-"
        print(
            f"  {ok} {r['ticket_id']}  {r['action']:<8} (exp {r['expected_action']:<8}) "
            f"conf={r['confidence']:.2f}  cited={cite}"
        )

    print("\n── metrics ─────────────────────────────────────────────────")
    print(f"  Action accuracy     : {pct(len(correct_action), n)}")
    print(f"  Deflection rate     : {pct(len(resolved), n)}")
    print(f"  Grounding rate      : {pct(len(grounded), len(resolved))}")
    print(f"  Citation accuracy   : {pct(len(cited_right), len(correct_deflect))}")
    print(f"  Escalation precision: {pct(len(true_escalations), len(escalated))}")
    print(f"  Latency             : {elapsed:.1f}s total, {elapsed / n:.1f}s/ticket")


if __name__ == "__main__":
    asyncio.run(_run())
