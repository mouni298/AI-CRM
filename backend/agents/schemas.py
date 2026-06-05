"""Structured outputs the agents are forced to return.

Using ADK `output_schema` (Pydantic) makes each agent's decision machine-readable
— which is what lets the eval harness score it and the glass-box trace log it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeflectionDecision(BaseModel):
    """The deflection agent's verdict on a single support ticket."""

    answer: str = Field(
        description="Customer-facing reply, grounded ONLY in the provided sources. "
        "Leave empty when escalating."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="0..1 confidence the answer fully resolves the ticket from the sources.",
    )
    cited_articles: list[str] = Field(
        default_factory=list,
        description="KB article ids actually used in the answer, e.g. ['kb-003'].",
    )
    should_escalate: bool = Field(
        description="True if the sources don't resolve it or it needs a human "
        "(billing disputes, data loss, legal/contract, bugs, feature requests).",
    )
    reason: str = Field(description="One-line rationale for the decision.")
