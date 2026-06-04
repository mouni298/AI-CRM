"""LLM wiring — Anthropic Claude through ADK's LiteLlm wrapper.

Two tiers per the plan: a fast/cheap model for triage + retrieval, a strong
model for reasoning/synthesis/outreach. Swapping to Gemini (ADK-native) is a
config change — set MODEL_FAST/MODEL_SMART to "gemini/..." in .env.
"""

from __future__ import annotations

from google.adk.models.lite_llm import LiteLlm

from . import config


def fast() -> LiteLlm:
    """Cheap model: classification/routing, retrieval, simple summaries."""
    return LiteLlm(model=config.MODEL_FAST)


def smart() -> LiteLlm:
    """Strong model: qualification reasoning, deflection answers, outreach drafts."""
    return LiteLlm(model=config.MODEL_SMART)
